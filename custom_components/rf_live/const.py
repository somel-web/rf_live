"""Constantes pour l'intégration RF Live."""
from datetime import timedelta

DOMAIN = "rf_live"

# Liste des chaînes supportées.
# ID 3 volontairement absent (vide côté Radio France).
# Volontairement exclues (cas à part, pas d'"émission" au sens classique) :
# - FIP : schéma JSON différent (titre de morceau / interprète)
# - France Info : ne s'applique pas à ce modèle now/next
# - Mouv : cas à part, musique plutôt qu'émissions
# France Musique : gardée mais non prioritaire, à valider plus tard.
CHANNELS: dict[str, str] = {
    "1": "France Inter",
    "4": "France Musique",  # à valider plus tard
    "5": "France Culture",
}

# Slug d'endpoint par chaîne, requis dans l'URL de l'API
# (https://api.radiofrance.fr/livemeta/live/{id}/{slug}).
# Seuls Inter et Culture sont confirmés (source : gist utilisateur).
# France Musique est une supposition par pattern, à vérifier/corriger en
# config (champ éditable) le jour où elle sera testée.
DEFAULT_ENDPOINT_SLUGS: dict[str, str] = {
    "1": "webrf_inter_player",  # confirmé
    "4": "webrf_musique_player",  # supposé, non testé
    "5": "webrf_culture_player",  # confirmé
}

CONF_CHANNEL = "channel"
CONF_ENDPOINT_SLUG = "endpoint_slug"
CONF_STREAM_URL = "stream_url"
CONF_GENERIC_IMAGE = "generic_image"
CONF_IMAGE_RESOLUTION = "image_resolution"

DEFAULT_IMAGE_RESOLUTION = "268x268"

API_URL = "https://api.radiofrance.fr/livemeta/live/{channel_id}/{slug}"
IMAGE_URL = "https://www.radiofrance.fr/pikapi/images/{visual_id}/{resolution}"

# Pas de système de cache : chaque fetch réussi replanifie le suivant
# exactement sur la valeur "delayToRefresh" (ms) renvoyée par l'API,
# qui est déjà synchronisée côté serveur avec le moment de la requête.
# Ces bornes sont uniquement défensives (valeur absente/aberrante),
# pas une politique de cache.
MIN_REFRESH_SECONDS = 5
MAX_REFRESH_SECONDS = 30 * 60
DEFAULT_REFRESH_SECONDS = 30
