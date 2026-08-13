"""DataUpdateCoordinator pour RF Live.

Pas de système de cache : chaque fetch réussi replanifie le suivant.
delayToRefresh (ms, renvoyé par l'API) s'est révélé peu fiable en
pratique : priorité à now.endTime (heure de fin réelle du step
courant), delayToRefresh/2 uniquement en repli. En cas d'échec, on
lève UpdateFailed (comportement standard HA : entités en
"unavailable", nouvelle tentative au prochain cycle), on ne garde pas
de dernière valeur valide en mémoire.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_URL,
    DEFAULT_REFRESH_SECONDS,
    END_OF_STEP_MARGIN_SECONDS,
    IMAGE_URL,
    MAX_REFRESH_SECONDS,
    MIN_REFRESH_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


def _build_image_url(visual_id: str | None, resolution: str, fallback: str) -> str:
    """Construit l'URL d'image à partir d'un ID visual, ou renvoie le fallback."""
    if not visual_id:
        return fallback
    return IMAGE_URL.format(visual_id=visual_id, resolution=resolution)


def _extract_info(
    step: dict[str, Any] | None,
    image_key: str,
    resolution: str,
    generic_image: str,
) -> dict[str, Any] | None:
    """Normalise un objet 'now'/'next[0]' de l'API en attributs exploitables."""
    if step is None:
        return None

    start_ts = step.get("startTime")
    end_ts = step.get("endTime")

    return {
        "nom_emission": (step.get("firstLine") or "").strip(),
        "jour": (step.get("secondLine") or "").strip(),
        "image": _build_image_url(step.get(image_key), resolution, generic_image),
        "debut": dt_util.as_local(dt_util.utc_from_timestamp(start_ts))
        if start_ts
        else None,
        "fin": dt_util.as_local(dt_util.utc_from_timestamp(end_ts)) if end_ts else None,
    }


class RFLiveUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator dédié à une chaîne (une config entry)."""

    def __init__(
        self,
        hass: HomeAssistant,
        channel_id: str,
        channel_name: str,
        endpoint_slug: str,
        stream_url: str,
        generic_image: str,
        resolution: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"rf_live_{channel_id}",
            update_interval=timedelta(seconds=DEFAULT_REFRESH_SECONDS),
        )
        self._channel_id = channel_id
        self.channel_name = channel_name
        self._endpoint_slug = endpoint_slug
        self.stream_url = stream_url
        self.generic_image = generic_image
        self._resolution = resolution

    async def _async_update_data(self) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)
        url = API_URL.format(channel_id=self._channel_id, slug=self._endpoint_slug)

        try:
            async with async_timeout.timeout(10):
                response = await session.get(url)
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(
                f"Échec du fetch API RF Live ({self.channel_name}) : {err}"
            ) from err

        now_info = _extract_info(
            payload.get("now"), "cover_square", self._resolution, self.generic_image
        )
        next_list = payload.get("next") or []
        next_info = _extract_info(
            next_list[0] if next_list else None,
            "cover",
            self._resolution,
            self.generic_image,
        )

        self.update_interval = self._compute_next_interval(payload)

        return {"current": now_info, "next": next_info}

    def _compute_next_interval(self, payload: dict[str, Any]) -> timedelta:
        """Replanifie le prochain fetch.

        `delayToRefresh` s'est révélé peu fiable en pratique. Priorité à
        `now.endTime` (heure de fin réelle du step courant, donnée
        indépendante et vérifiable) ; `delayToRefresh` n'est utilisé qu'en
        repli, et divisé par 2 par précaution puisqu'il n'est pas fiable.
        """
        now_step = payload.get("now") or {}
        end_ts = now_step.get("endTime")

        if isinstance(end_ts, (int, float)) and end_ts > 0:
            now_ts = dt_util.utcnow().timestamp()
            delay_seconds = end_ts - now_ts + END_OF_STEP_MARGIN_SECONDS
            source = "now.endTime"
        else:
            delay_ms = payload.get("delayToRefresh")
            if isinstance(delay_ms, (int, float)) and delay_ms > 0:
                # Divisé par 2 : delayToRefresh s'est montré peu fiable,
                # on préfère repasser plus tôt que de rater un changement.
                delay_seconds = (delay_ms / 1000) / 2
                source = "delayToRefresh/2"
            else:
                delay_seconds = DEFAULT_REFRESH_SECONDS
                source = "défaut"

        delay_seconds = max(delay_seconds, MIN_REFRESH_SECONDS)
        delay_seconds = min(delay_seconds, MAX_REFRESH_SECONDS)

        _LOGGER.debug(
            "RF Live (%s) : prochain fetch dans %.0fs (source : %s)",
            self.channel_name,
            delay_seconds,
            source,
        )

        return timedelta(seconds=delay_seconds)
