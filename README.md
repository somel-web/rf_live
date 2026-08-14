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

## Media player enrichi (image + titre natifs dans la carte "Media control")

Le problème de base : un `media_player` "bête" (ex. une enceinte qui ne fait que jouer l'URL du flux, sans rien connaître du contenu) n'a pas d'`entity_picture` — la carte HA native `media-control` n'a alors rien à afficher en fond. Forcer une image via `card_mod` sur cette carte est fragile (structure interne changeante selon les versions de HA) et ne fait que cacher le vrai problème : l'entité elle-même n'a pas la bonne donnée.

**Solution : combiner l'enceinte réelle avec `sensor.<chaine>_en_cours` via [ha-custom-universal-media-player](https://github.com/bastgau/ha-custom-universal-media-player)** (HACS, config UI complète, pas de YAML à écrire dans `configuration.yaml`). Ce fork corrige spécifiquement une limitation de l'intégration native "Universal Media Player" qui ne pouvait pas accéder à certains attributs des enfants — dont `entity_picture`.

### Mise en place

1. **HACS > ⋮ > Dépôts personnalisés** > ajouter `github.com/bastgau/ha-custom-universal-media-player` (catégorie Intégration). Nécessite HA 2026.7.0+.
2. Installer, puis **redémarrer HA** (redémarrage complet requis pour une nouvelle intégration).
3. **Réglages > Appareils et services > Ajouter une intégration** > rechercher l'intégration. Nommer l'entité, sélectionner l'enceinte réelle (ex. `media_player.salon_bose`) comme unique enfant.
4. **Configurer les commandes** (mode guidé) : pour chaque commande (lecture, pause, volume...), cibler l'enceinte réelle.
5. **Surcharger les attributs** (section "Configure attributes", YAML personnalisé) :
   ```yaml
   media_title: sensor.france_inter_en_cours
   media_artist: sensor.france_inter_en_cours|jour
   entity_picture: sensor.france_inter_en_cours|image
   ```
   Syntaxe : `entity_id` seul → prend l'état de cette entité ; `entity_id|attribut` → prend un attribut spécifique. `media_title` prend donc l'état du sensor (nom de l'émission), les deux autres pointent vers ses attributs.
6. Finaliser. La nouvelle entité `media_player` doit apparaître dans **Outils de développement > États** avec les bons `media_title`/`media_artist`/`entity_picture` dès que la chaîne configurée joue sur l'enceinte.

### Carte Lovelace

```yaml
type: media-control
entity: media_player.<la_nouvelle_entité>
```

Plus besoin de `card_mod` ni de hack CSS : la carte native affiche directement le fond flouté et le texte à partir des vrais attributs de l'entité. Validé en conditions réelles (voir capture du 14/08/2026).

---

## Piste explorée et mise en réserve : relais ICY pour Music Assistant

Radio France n'implémentant pas le protocole ICY sur ses flux (pas de `StreamTitle` natif), un projet séparé (`rf_icy_relay`, non inclus dans ce repo) a été développé pour relayer l'audio en y injectant de vraies métadonnées ICY construites à partir de cette même API `livemeta/live`. Fonctionnel pour le titre (confirmé avec VLC et Music Assistant), mais l'image (`StreamUrl`, convention informelle ICY) n'est pas exploitée de façon fiable par Music Assistant en pratique — mis de côté pour ce cas d'usage précis, la découverte reste valable pour d'autres applications qui liraient correctement ce champ.

## À garder en mémoire (pas encore implémenté)

Constaté sur le JSON de l'API : `now.endTime` peut être supérieur à `next.startTime` (chevauchement/battement de grille). Se caler sur `endTime` peut donc refetch avant le vrai basculement. Piste retenue pour une prochaine itération : aligner la replanification sur `next.startTime` plutôt que `now.endTime`, avec un retry à 1 min si le fetch suivant ne montre toujours pas de changement (cas retard de diffusion).
