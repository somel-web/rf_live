"""DataUpdateCoordinator pour RF Live.

Stratégie de cache :
- fetch initial au démarrage
- à chaque fetch réussi, calcule le step "courant" et le step "suivant"
  à partir de la fenêtre glissante renvoyée par l'API (voir levels[-1])
- replanifie dynamiquement le prochain fetch à l'heure de fin du step
  courant (+ marge), plafonné par un garde-fou périodique (GUARD_INTERVAL)
  et un minimum (MIN_UPDATE_INTERVAL_SECONDS)
- en cas d'échec API, conserve la dernière donnée valide en cache
  (pas de passage en unavailable) et retente après le garde-fou
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    API_URL,
    END_OF_STEP_MARGIN_SECONDS,
    GUARD_INTERVAL,
    IMAGE_URL,
    MIN_UPDATE_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


def _build_image_url(visual_id: str | None, resolution: str, fallback: str) -> str:
    """Construit l'URL d'image à partir d'un ID visual, ou renvoie le fallback."""
    if not visual_id:
        return fallback
    return IMAGE_URL.format(visual_id=visual_id, resolution=resolution)


def _extract_step_info(
    step: dict[str, Any] | None,
    resolution: str,
    generic_image: str,
) -> dict[str, Any] | None:
    """Normalise un step brut de l'API en dict d'attributs exploitables."""
    if step is None:
        return None

    start_ts = step.get("start")
    end_ts = step.get("end")

    sous_titre = step.get("titleSlug") or ""
    if sous_titre:
        sous_titre = sous_titre.replace("-", " ")
        sous_titre = sous_titre[:1].upper() + sous_titre[1:]

    return {
        "title": step.get("title") or step.get("titleSlug") or "",
        "sous_titre": sous_titre,
        "nom_emission": (step.get("titleConcept") or "").strip(),
        "image": _build_image_url(step.get("visual"), resolution, generic_image),
        "image_banner": _build_image_url(
            step.get("visualBanner") or step.get("visual"), resolution, generic_image
        ),
        "debut": dt_util.as_local(dt_util.utc_from_timestamp(start_ts))
        if start_ts
        else None,
        "fin": dt_util.as_local(dt_util.utc_from_timestamp(end_ts)) if end_ts else None,
        "_end_ts": end_ts,
    }


class RFLiveUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator dédié à une chaîne (une config entry)."""

    def __init__(
        self,
        hass: HomeAssistant,
        channel_id: str,
        channel_name: str,
        stream_url: str,
        generic_image: str,
        resolution: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"rf_live_{channel_id}",
            update_interval=timedelta(seconds=MIN_UPDATE_INTERVAL_SECONDS),
        )
        self._channel_id = channel_id
        self.channel_name = channel_name
        self.stream_url = stream_url
        self.generic_image = generic_image
        self._generic_image = generic_image
        self._resolution = resolution
        self._last_valid_data: dict[str, Any] | None = None
        self._consecutive_failures = 0

    async def _async_update_data(self) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)
        url = API_URL.format(channel_id=self._channel_id)

        try:
            async with async_timeout.timeout(10):
                response = await session.get(url)
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except Exception as err:  # noqa: BLE001 - on log et on garde le cache
            self._consecutive_failures += 1
            # Backoff progressif court plutôt que de sauter direct au
            # garde-fou de 45 min : si l'échec survient pile au moment où
            # la fenêtre devrait basculer (fin de step), on veut reprendre
            # vite pour éviter d'afficher un cache avec debut/fin déjà
            # dépassés pendant un cycle entier de 45 min.
            backoff_seconds = min(
                MIN_UPDATE_INTERVAL_SECONDS * (2 ** (self._consecutive_failures - 1)),
                GUARD_INTERVAL.total_seconds(),
            )
            _LOGGER.warning(
                "RF Live (%s) : échec du fetch API (%s), nouvelle tentative dans %.0fs "
                "(échec consécutif n°%d), conservation du dernier cache valide",
                self.channel_name,
                err,
                backoff_seconds,
                self._consecutive_failures,
            )
            if self._last_valid_data is not None:
                self.update_interval = timedelta(seconds=backoff_seconds)
                current = self._last_valid_data.get("current") or {}
                stale_end_ts = current.get("_end_ts")
                if stale_end_ts:
                    staleness_min = (dt_util.utcnow().timestamp() - stale_end_ts) / 60
                    if staleness_min > 0:
                        _LOGGER.warning(
                            "RF Live (%s) : cache servi périmé depuis %.1f min "
                            "(fin théorique du step courant dépassée)",
                            self.channel_name,
                            staleness_min,
                        )
                return self._last_valid_data
            # Pas de cache du tout (ex. premier démarrage) : on laisse
            # remonter l'erreur pour un ConfigEntryNotReady propre.
            raise

        parsed = self._parse_payload(payload)
        self._consecutive_failures = 0
        self._last_valid_data = parsed
        self.update_interval = self._compute_next_interval(parsed)
        return parsed

    def _parse_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        levels = payload.get("levels") or []
        steps = payload.get("steps") or {}

        if not levels:
            _LOGGER.warning(
                "RF Live (%s) : réponse API sans 'levels', conservation du dernier cache",
                self.channel_name,
            )
            if self._last_valid_data is not None:
                return self._last_valid_data
            raise ValueError("Réponse API RF Live invalide : pas de 'levels'")

        # Toujours prendre le DERNIER niveau : certaines chaînes (FIP) peuvent
        # avoir 2 niveaux pendant des émissions spéciales, le niveau utile
        # est alors le dernier, pas le premier.
        last_level = levels[-1]
        items: list[str] = last_level.get("items", [])
        position: int = last_level.get("position", 0)

        current_step_id = items[position] if 0 <= position < len(items) else None
        next_step_id = (
            items[position + 1] if 0 <= position + 1 < len(items) else None
        )

        current_step = steps.get(current_step_id) if current_step_id else None
        next_step = steps.get(next_step_id) if next_step_id else None

        current_info = _extract_step_info(
            current_step, self._resolution, self._generic_image
        )
        next_info = _extract_step_info(
            next_step, self._resolution, self._generic_image
        )

        return {"current": current_info, "next": next_info}

    def _compute_next_interval(self, parsed: dict[str, Any]) -> timedelta:
        """Calcule le délai avant le prochain fetch.

        Se cale sur la fin du step courant (+ marge), plafonné par le
        garde-fou périodique, et jamais en dessous du minimum autorisé.
        """
        current = parsed.get("current")
        end_ts = current.get("_end_ts") if current else None

        if not end_ts:
            return GUARD_INTERVAL

        now_ts = dt_util.utcnow().timestamp()
        seconds_until_end = end_ts - now_ts + END_OF_STEP_MARGIN_SECONDS

        delay = max(seconds_until_end, MIN_UPDATE_INTERVAL_SECONDS)
        delay = min(delay, GUARD_INTERVAL.total_seconds())

        return timedelta(seconds=delay)
