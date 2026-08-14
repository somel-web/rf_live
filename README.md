# RF Live

Intégration Home Assistant custom exposant l'émission en cours (et suivante) sur une chaîne Radio France : nom du programme, titre du jour, image. Basée sur l'API `livemeta/live` (now/next/delayToRefresh), pas de système de cache.

## Installation

Copier le dossier `custom_components/rf_live/` dans le dossier `custom_components` de ta config HA, puis redémarrer HA. HACS-compatible (repo custom).

## Configuration

Réglages > Appareils et services > Ajouter une intégration > RF Live.

Une instance = une chaîne. Ajouter l'intégration plusieurs fois pour plusieurs chaînes.

Étape 1 : choix de la chaîne.
Étape 2 :
- **Slug de l'endpoint API** (pré-rempli, **confirmé uniquement pour Inter et Culture** — vérifier/corriger pour Musique si l'intégration ne remonte rien après l'ajout)
- **URL du flux audio**
- **URL de l'image générique de la chaîne** (fallback si l'API ne fournit pas d'image)
- **Résolution des images** (ex. `268x268`, carré, un seul champ)

Ces mêmes champs sont modifiables après coup via le menu Options de l'intégration (⋮ sur l'entrée dans Appareils et services), sans devoir la retirer/rajouter.

## Entités créées (par instance)

- `sensor.<chaine>_en_cours` : état = nom du programme (`firstLine`), attributs = `jour` (`secondLine`), `image` (`cover_square`), `debut`, `fin`, `stream_url`, `image_generique`
- `sensor.<chaine>_suivant` : même structure, image basée sur `cover` (`next[0]`)
- `button.<chaine>_forcer_la_mise_a_jour` : force un refresh immédiat (passe par le debouncer du coordinator)

## Chaînes volontairement exclues

- **FIP** : schéma JSON différent (titre de morceau / interprète / album, pas d'émission)
- **France Info** : ne s'applique pas à ce modèle now/next
- **Mouv** : cas à part, musique plutôt qu'émissions

**France Musique** est présente dans la liste mais son slug n'est pas confirmé — à valider plus tard.

## Fonctionnement

Chaque fetch réussi replanifie le suivant sur la valeur `delayToRefresh` (ms) renvoyée par l'API, déjà synchronisée côté serveur. Pas de cache : en cas d'échec, l'entité passe en `unavailable` jusqu'au prochain cycle (comportement standard HA via `UpdateFailed`).

---

## Cartes Lovelace

Deux approches, du plus simple au plus abouti. Voir aussi `lovelace_example.yaml` dans ce repo.

### Option 1 — Markdown (recommandée si tu veux éviter toute dépendance)

Native HA core, templates Jinja2 supportés nativement, pas de dépendance HACS.

```yaml
type: markdown
content: >
  ## {{ states('sensor.france_inter_en_cours') }}

  {{ state_attr('sensor.france_inter_en_cours', 'jour') }}


  <img src="{{ state_attr('sensor.france_inter_en_cours', 'image') }}" width="268">


  ---


  **À suivre :** {{ states('sensor.france_inter_suivant') }}
  — {{ state_attr('sensor.france_inter_suivant', 'jour') }}
```

`<img>` en HTML brut plutôt que la syntaxe `![]()` pure : permet de fixer la taille d'affichage (la syntaxe markdown pure ne le permet pas).

### Option 2 — Image en fond, bandeau opaque avec le jour en bas

Nécessite **`config-template-card`** (HACS) : `picture-elements` seule ne permet pas de templater le champ `image:` avec un attribut d'entité.

Nécessite aussi **`card_mod`** (HACS) : le composant interne `state-label` de HA applique `white-space: nowrap` + `overflow: hidden` + `text-overflow: ellipsis` sur un nœud qu'un simple `style:` inline ne peut pas atteindre, même avec `!important` — `card_mod` injecte une vraie balise `<style>` dans le shadow DOM du composant, qui elle est bien prioritaire.

```yaml
type: custom:config-template-card
entities:
  - sensor.france_inter_en_cours
card:
  type: picture-elements
  image: >-
    ${states['sensor.france_inter_en_cours'].attributes.image}
  elements:
    - type: state-label
      entity: sensor.france_inter_en_cours
      attribute: jour
      style:
        top: 85%
        left: 0%
        right: 0%
        height: 15%
        transform: initial
        background-color: rgba(0, 0, 0, 0.4)
        color: white
        font-size: 0.9em
        display: flex
        align-items: center
        justify-content: center
        text-align: center
      card_mod:
        style: |
          div {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
          }
```

Le nom de l'émission n'est pas dupliqué en overlay : il est déjà présent visuellement dans l'image fournie par l'API. Validé en conditions réelles (texte long sur 2 lignes, wrap et centrage corrects).

---

## Media player enrichi (image dans une vraie carte de contrôle)

Le problème de base : un `media_player` "bête" (ex. une enceinte qui ne fait que jouer l'URL du flux, sans rien connaître du contenu) n'a pas d'`entity_picture` — la carte HA native `media-control` n'a alors rien à afficher en fond.

Plusieurs approches ont été explorées (intégration HACS tierce pour combiner/surcharger l'entité, `template:` natif — qui ne supporte en réalité **aucune plateforme `media_player`**, contrairement à ce qu'on pourrait penser en lisant sa doc en diagonale) avant de converger sur la plus simple : **[Yet Another Media Player (YAMP)](https://github.com/jianyu-li/yet-another-media-player)** (carte Lovelace custom, HACS), qui supporte nativement la surcharge d'artwork par correspondance sur le flux joué — exactement ce qu'il fallait, sans toucher à l'entité elle-même.

### Carte YAMP

```yaml
type: custom:yet-another-media-player
entities:
  - media_player.salon_bose
media_artwork_overrides:
  - image_url: "{{ state_attr('sensor.france_inter_en_cours', 'image') }}"
    media_content_id: "*franceinter*"
  - image_url: "{{ state_attr('sensor.france_culture_en_cours', 'image') }}"
    media_content_id: "*franceculture*"
```

`media_content_id` correspond à l'URL du flux passée au moment du `play_media` sur l'enceinte réelle — le wildcard (`*franceinter*`) tolère les variantes de qualité/format (`franceinter-hifi.aac` vs `franceinter-midfi.mp3` par exemple). `image_url` accepte un template Jinja résolu dynamiquement, donc l'image suit en direct l'émission en cours.

**Limite assumée** : YAMP ne surcharge que l'artwork, pas le texte (titre/artiste restent ceux que l'entité native rapporte — généralement vide pour un flux brut). Ce n'est pas un problème ici puisque le nom de l'émission est déjà visible dans l'image fournie par l'API RF elle-même (cf. les visuels avec titre incrusté). Pour un détail texte (jour, émission suivante), une carte séparée suffit :

```yaml
type: markdown
content: >
  {{ state_attr('sensor.france_inter_en_cours', 'jour') }}


  **À suivre :** {{ states('sensor.france_inter_suivant') }}
  — {{ state_attr('sensor.france_inter_suivant', 'jour') }}
```

### Pistes abandonnées (gardées en note pour éviter de les réexplorer)

- **`ha-custom-universal-media-player`** (HACS) + sensor template intermédiaire : fonctionnel mais nécessite deux mécanismes différents pour un seul résultat, alors que YAMP fait la même chose nativement en un bloc.
- **`template: - media_player:`** : n'existe pas. La liste officielle des plateformes supportées par l'intégration `template` ne contient pas `media_player` (alarm control panel, binary sensor, button, cover, device tracker, event, fan, image, light, lock, number, select, sensor, switch, update, vacuum, weather — c'est tout). Une config `template:` avec un bloc `media_player:` est silencieusement ignorée par HA, qui ne garde que le trigger — d'où le repair "trigger orphelin".
- **Relais ICY pour Music Assistant** (`rf_icy_relay`, projet séparé, non inclus dans ce repo) : fonctionnel pour le titre (confirmé avec VLC et Music Assistant), mais nécessite de router l'audio via Music Assistant plutôt que directement vers l'enceinte — mis de côté une fois YAMP identifié comme solution plus directe pour ce cas d'usage. Reste une découverte valable pour d'autres projets.

## À garder en mémoire (pas encore implémenté)

Constaté sur le JSON de l'API : `now.endTime` peut être supérieur à `next.startTime` (chevauchement/battement de grille). Se caler sur `endTime` peut donc refetch avant le vrai basculement. Piste retenue pour une prochaine itération : aligner la replanification sur `next.startTime` plutôt que `now.endTime`, avec un retry à 1 min si le fetch suivant ne montre toujours pas de changement (cas retard de diffusion).
