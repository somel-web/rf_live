# RF Live

Intégration Home Assistant custom exposant l'émission en cours (et suivante) sur une chaîne Radio France : titre du jour, nom d'émission, description, image.

## Installation

Copier le dossier `custom_components/rf_live/` dans le dossier `custom_components` de ta config HA, puis redémarrer HA. HACS-compatible (repo custom).

## Configuration

Réglages > Appareils et services > Ajouter une intégration > RF Live.

Une instance = une chaîne. Ajouter l'intégration plusieurs fois pour plusieurs chaînes.

Champs demandés :
- Chaîne (liste déroulante)
- URL du flux audio (entrée manuelle)
- URL de l'image générique de la chaîne (fallback si l'API ne fournit pas d'image pour un step)
- Résolution des images (ex. `268x268`, appliquée en carré, un seul champ pour largeur=hauteur)

## Entités créées (par instance)

- `sensor.<chaine>_en_cours` : état = titre du jour, attributs = nom_emission, description, image, image_banner, debut, fin, stream_url, image_generique
- `sensor.<chaine>_suivant` : même structure, pour l'émission suivante

## Notes techniques

- Toujours parser `levels[-1]` (pas `levels[0]`) : sur FIP, `levels` peut contenir 2 entrées pendant certaines émissions spéciales.
- Fenêtre API : nombre d'items fixe autour de la position courante (pas une plage horaire fixe). Le step "suivant" est systématiquement présent dans la même réponse.
- Cache : reschedule dynamique à la fin du step courant (+5s de marge), plafonné par un garde-fou de 45 min, minimum 30s entre deux fetchs.
- En cas d'échec API : conservation du dernier cache valide, pas de passage en `unavailable`.

Voir `lovelace_example.yaml` pour un exemple de carte (nécessite `config-template-card` via HACS pour l'image dynamique).
