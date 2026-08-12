"""Constantes pour l'intégration RF Live."""
from datetime import timedelta

DOMAIN = "rf_live"

# Liste corrigée des chaînes Radio France exposant l'API livemeta.
# ID 3 volontairement absent (vide côté Radio France).
CHANNELS: dict[str, str] = {
    "1": "France Inter",
    "2": "France Info",
    "4": "France Musique",
    "5": "France Culture",
    "6": "Mouv",
    "7": "FIP",
}

CONF_CHANNEL = "channel"
CONF_STREAM_URL = "stream_url"
CONF_GENERIC_IMAGE = "generic_image"
CONF_IMAGE_RESOLUTION = "image_resolution"

DEFAULT_IMAGE_RESOLUTION = "268x268"

API_URL = "https://api.radiofrance.fr/livemeta/pull/{channel_id}"
IMAGE_URL = "https://www.radiofrance.fr/pikapi/images/{visual_id}/{resolution}"

# Garde-fou périodique : refetch forcé même si le step courant est très long,
# pour suivre le glissement de la fenêtre et détecter d'éventuels changements
# de grille. Confirmé par test réel que la fenêtre laisse une marge d'avance
# suffisante (~1h+) pour que 45 min soit un intervalle sûr par défaut.
GUARD_INTERVAL = timedelta(minutes=45)

# Marge ajoutée après l'heure de fin théorique d'un step avant de refetch,
# pour laisser le temps à l'API de basculer sur le step suivant.
END_OF_STEP_MARGIN_SECONDS = 5

# Intervalle minimum entre deux fetchs, quelle que soit la situation,
# pour éviter tout risque de boucle serrée sur des données incohérentes.
MIN_UPDATE_INTERVAL_SECONDS = 30
