# trace2svg — vectorisation centerline pour traceur à stylo

Convertit une image raster (PNG, JPG, WebP…) d'un **dessin au trait monoligne**
(encre noire, épaisseur uniforme, sans aplats ni hachures) en **SVG prêt à
tracer** : chaque trait devient un chemin vectoriel unique passant par le
**centre de la ligne** (squelettisation), et non un contour doublé autour du
trait comme le ferait un vectoriseur classique (potrace, Inkscape « Vectoriser
le bitmap » par défaut).

Le résultat est ensuite optimisé avec [vpype](https://github.com/abey79/vpype) :

- `linemerge` — fusion des tracés dont les extrémités sont proches ;
- `reloop` — déplacement du point de départ des chemins fermés ;
- `linesort` — tri des tracés pour minimiser les déplacements plume levée ;
- `linesimplify` — simplification des nœuds superflus.

## Installation

```bash
pip install -r requirements.txt
```

(Python ≥ 3.11 requis par vpype 1.15.)

## Utilisation

```bash
# Cas simple : dessin noir sur fond clair, échelle native (96 px/pouce)
python3 trace2svg.py dessin.png

# Sortie de 150 mm de large (proportions conservées) avec 10 mm de marge
python3 trace2svg.py dessin.png -o dessin.svg --width 150 --margin 10

# Traits clairs sur fond sombre (tableau noir, néon…)
python3 trace2svg.py photo_tableau.jpg --invert

# Scan bruité : seuil manuel, flou léger, réparation des micro-coupures
python3 trace2svg.py scan.jpg --threshold 190 --blur 1 --close 1 --despeckle 25
```

Formats de papier courants : `--width 190` pour un A4 portrait avec marges,
`--width 138` pour un A5.

## Options

| Option | Unité | Défaut | Rôle |
|---|---|---|---|
| `-o, --output` | chemin | entrée en `.svg` | Fichier SVG de sortie |
| `--width` | mm | — | Largeur physique du dessin, proportions conservées |
| `--margin` | mm | 0 | Marge de page autour du dessin |
| `--threshold` | 0–255 | Otsu auto | Seuil de binarisation (encre = plus sombre) |
| `--invert` | — | off | Traits clairs sur fond sombre |
| `--blur` | px (σ) | 0 | Flou gaussien avant seuillage |
| `--close` | itérations | 0 | Fermeture morphologique 3×3 (micro-coupures) |
| `--despeckle` | px² | 9 | Supprime les composantes < N pixels |
| `--prune` | px | 5 | Supprime les barbules du squelette < N px |
| `--min-length` | px | 0 | Ignore les tracés plus courts que N px |
| `--merge-tol` | mm | 0,3 | Tolérance de fusion des extrémités |
| `--simplify-tol` | mm | 0,1 | Tolérance de simplification |
| `-v, --verbose` | — | off | Statistiques sur stderr |

Codes de sortie : `0` succès, `1` échec ou **aucun trait détecté** (message
explicite sur stderr, aucun fichier écrit), `2` erreur d'usage.

`--width` s'applique à la boîte englobante du **dessin** (les marges blanches
de l'image source ne comptent pas) ; la page SVG vaut cette boîte plus deux
fois `--margin`. La mise à l'échelle est appliquée **avant** l'optimisation,
si bien que les tolérances en millimètres correspondent aux dimensions
physiques réelles du tracé final.

## Exemple

`examples/make_example.py` régénère à l'identique un portrait synthétique et
sa vectorisation de référence (`portrait_demo.png` → `portrait_demo.svg`,
commités comme référence du résultat attendu).

## Tests

```bash
pip install -r requirements-dev.txt
python3 -m pytest tests -q
```

La suite contient notamment une preuve quantitative du traçage centerline :
un cercle de rayon r au trait de 3 px doit donner un unique chemin de
longueur ≈ 2πr — un vectoriseur par contours en produirait ≈ 4πr.

## Limites

- Conçu pour des dessins **monolignes** : les aplats et traits très épais
  sont réduits à leur squelette (une épaisseur > ~10 px produit des
  artefacts de squelettisation) ; les hachures denses fusionnent.
- Le tri `linesort` est un glouton avec repasses : très bon en pratique,
  pas garanti optimal.
