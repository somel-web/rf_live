# RF Live

Intégration Home Assistant custom exposant l'émission en cours (et suivante) sur une chaîne Radio France : nom du programme, titre du jour, image. Basée sur l'API `livemeta/live` (now/next/delayToRefresh), pas de système de cache.

## Installation

Copier le dossier `custom_components/rf_live/` dans le dossier `custom_components` de ta config HA, puis redémarrer HA. HACS-compatible (repo custom).

## Configuration

Réglages > Appareils et services > Ajouter une intégration > RF Live.

Une instance = une chaîne. Ajouter l'intégration plusieurs fois pour plusieurs chaînes.

Étape 1 : choix de la chaîne.
Étape 2 :
- Slug de l'endpoint API (pré-rempli, **confirmé uniquement pour Inter et Culture** — vérifier/corriger pour Musique si l'intégration ne remonte rien après l'ajout)
- URL du flux audio
- URL de l'image générique de la chaîne (fallback si l'API ne fournit pas d'image)
- Résolution des images (ex. `268x268`, carré, un seul champ)

## Entités créées (par instance)

- `sensor.<chaine>_en_cours` : état = nom du programme (`firstLine`), attributs = jour (`secondLine`), image (`cover_square`), debut, fin, stream_url, image_generique
- `sensor.<chaine>_suivant` : même structure, image basée sur `cover` (`next[0]`)
- `button.<chaine>_forcer_la_mise_a_jour` : force un refresh immédiat (passe par le debouncer du coordinator)

## Chaînes volontairement exclues

- **FIP** : schéma JSON différent (titre de morceau / interprète / album, pas d'émission)
- **France Info** : ne s'applique pas à ce modèle now/next
- **Mouv** : cas à part, musique plutôt qu'émissions

**France Musique** est présente dans la liste mais son slug n'est pas confirmé — à valider plus tard.

## Fonctionnement

Chaque fetch réussi replanifie le suivant sur la valeur `delayToRefresh` (ms) renvoyée par l'API, déjà synchronisée côté serveur. Pas de cache : en cas d'échec, l'entité passe en `unavailable` jusqu'au prochain cycle (comportement standard HA via `UpdateFailed`).

Voir `lovelace_example.yaml` pour un exemple de carte (nécessite `config-template-card` via HACS pour l'image dynamique).
