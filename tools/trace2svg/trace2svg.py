#!/usr/bin/env python3
"""trace2svg — vectorisation « centerline » d'un dessin au trait pour traceur à stylo.

Convertit une image raster (PNG/JPG/WebP…) d'un dessin monoligne (encre noire,
épaisseur de trait uniforme, sans aplats ni hachures) en SVG prêt à tracer :
chaque trait devient UN chemin vectoriel passant par le centre de la ligne
(squelettisation), puis le résultat est optimisé avec vpype (fusion des
extrémités proches, rebouclage des chemins fermés, tri minimisant les
déplacements plume levée, simplification des nœuds).

Exemple :
    python3 trace2svg.py dessin.png -o dessin.svg --width 150 --margin 10

Sans trait détecté, le script affiche un message et sort avec le code 1 sans
écrire de fichier. Pour des traits clairs sur fond sombre, utiliser --invert.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np


# Offsets 8-connexité : orthogonaux puis diagonaux.
_ORTHO = ((-1, 0), (1, 0), (0, -1), (0, 1))
_DIAG = ((-1, -1), (-1, 1), (1, -1), (1, 1))


def load_grayscale(path: str) -> np.ndarray:
    """Charge l'image en niveaux de gris uint8, en aplatissant une éventuelle
    transparence sur fond blanc (un PNG à fond transparent doit se comporter
    comme un dessin sur papier blanc)."""
    from PIL import Image

    img = Image.open(path)
    if img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        fond = Image.new("RGBA", img.size, (255, 255, 255, 255))
        fond.alpha_composite(img)
        img = fond
    return np.asarray(img.convert("L"), dtype=np.uint8)


def binarize(
    gray: np.ndarray,
    threshold: int | None = None,
    invert: bool = False,
    blur: float = 0.0,
    close: int = 0,
    despeckle: int = 9,
) -> tuple[np.ndarray, float | None]:
    """Binarise l'image : renvoie (masque booléen de l'encre, seuil utilisé).

    Le seuil utilisé vaut None si l'image est constante (aucune encre
    détectable) et qu'aucun seuil explicite n'a été fourni.
    """
    import scipy.ndimage
    import skimage.filters
    import skimage.morphology

    work = gray.astype(np.float64)
    if blur > 0:
        work = skimage.filters.gaussian(work, sigma=blur, preserve_range=True)

    if threshold is not None:
        t = float(threshold)
    elif work.min() == work.max():
        # threshold_otsu lève une erreur sur une image constante : image
        # uniformément vide (ou uniformément pleine), donc aucun trait.
        return np.zeros(gray.shape, dtype=bool), None
    else:
        t = float(skimage.filters.threshold_otsu(work))

    ink = work < t
    if invert:
        ink = ~ink

    if close > 0:
        ink = scipy.ndimage.binary_closing(
            ink, structure=np.ones((3, 3), dtype=bool), iterations=close
        )
    if despeckle > 0:
        # max_size retire les composantes de taille <= N (scikit-image 0.26),
        # soit l'équivalent de l'ancien min_size=N qui retirait les < N.
        ink = skimage.morphology.remove_small_objects(
            ink, max_size=despeckle - 1, connectivity=2
        )
    return ink, t


def _reduced_neighbors(skel: np.ndarray) -> dict[tuple[int, int], list[tuple[int, int]]]:
    """Adjacence 8-connexité « réduite » : un lien diagonal ne compte que si
    les deux pixels orthogonaux partagés sont vides. Élimine les triangles
    fantômes aux jonctions ; la même adjacence sert aux degrés et au parcours."""
    S = np.pad(skel, 1, constant_values=False)
    nbrs: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for r, c in np.argwhere(S):
        voisins = []
        for dr, dc in _ORTHO:
            if S[r + dr, c + dc]:
                voisins.append((r + dr, c + dc))
        for dr, dc in _DIAG:
            if S[r + dr, c + dc] and not S[r + dr, c] and not S[r, c + dc]:
                voisins.append((r + dr, c + dc))
        nbrs[(r, c)] = voisins
    return nbrs


def skeleton_to_polylines(
    skel: np.ndarray,
) -> tuple[list[np.ndarray], list[tuple[int, int]]]:
    """Convertit un squelette 1 px en polylignes.

    Renvoie (polylignes, degrés) où chaque polyligne est un tableau 1D complexe
    (x + iy, coordonnées image en pixels, sommets au centre des pixels) et
    degrés[i] = (degré du premier point, degré du dernier point) de la chaîne i
    dans le graphe du squelette — nécessaire à l'élagage des barbules.
    """
    nbrs = _reduced_neighbors(skel)
    deg = {p: len(v) for p, v in nbrs.items()}
    nodes = {p for p, d in deg.items() if d != 2}
    visited_edges: set[frozenset] = set()
    visited_px: set[tuple[int, int]] = set()
    chains: list[list[tuple[int, int]]] = []
    end_degrees: list[tuple[int, int]] = []

    # Passe 1 : chaînes ouvertes et chaînes jonction↔jonction.
    for p in nodes:
        if deg[p] == 0:
            continue  # pixel isolé : ignoré (relève du despeckle)
        for q in nbrs[p]:
            e = frozenset((p, q))
            if e in visited_edges:
                continue
            visited_edges.add(e)
            path = [p, q]
            prev, cur = p, q
            while cur not in nodes:
                visited_px.add(cur)
                a, b = nbrs[cur]
                nxt = b if a == prev else a
                path.append(nxt)
                prev, cur = cur, nxt
            visited_edges.add(frozenset((prev, cur)))
            chains.append(path)
            end_degrees.append((deg[path[0]], deg[path[-1]]))

    # Passe 2 : les pixels de degré 2 restants forment des boucles fermées pures.
    for s, d in deg.items():
        if d != 2 or s in nodes or s in visited_px:
            continue
        path = [s]
        visited_px.add(s)
        prev, cur = s, nbrs[s][0]
        while cur != s:
            visited_px.add(cur)
            path.append(cur)
            a, b = nbrs[cur]
            nxt = b if a == prev else a
            prev, cur = cur, nxt
        path.append(s)  # fermeture explicite de la boucle
        chains.append(path)
        end_degrees.append((2, 2))

    # (ligne, colonne) rembourrées -> complexe x + iy, offset centre de pixel.
    polylines = [
        np.array([(c - 1 + 0.5) + 1j * (r - 1 + 0.5) for r, c in path])
        for path in chains
    ]
    return polylines, end_degrees


def polyline_length(line: np.ndarray) -> float:
    """Longueur d'une polyligne complexe (px)."""
    return float(np.abs(np.diff(line)).sum()) if len(line) > 1 else 0.0


def prune_spurs(
    polylines: list[np.ndarray],
    end_degrees: list[tuple[int, int]],
    prune_px: float,
) -> list[np.ndarray]:
    """Supprime les barbules du squelette : chaînes plus courtes que prune_px
    dont une extrémité est une jonction (degré >= 3) et l'autre une pointe
    libre (degré 1). Les petits traits isolés (1-1) ne sont pas touchés."""
    if prune_px <= 0:
        return list(polylines)
    keep = []
    for line, (d0, d1) in zip(polylines, end_degrees):
        est_barbule = (
            polyline_length(line) < prune_px
            and ((d0 >= 3 and d1 == 1) or (d0 == 1 and d1 >= 3))
        )
        if not est_barbule:
            keep.append(line)
    return keep


def build_document(
    polylines: list[np.ndarray],
    width_mm: float | None,
    margin_mm: float,
):
    """Construit le Document vpype, mis à l'échelle AVANT l'optimisation pour
    que les tolérances exprimées en mm soient physiquement exactes.

    --width s'applique à la boîte englobante du dessin (pas au cadre de
    l'image source) ; la page vaut cette boîte plus 2 x --margin.
    """
    import vpype

    doc = vpype.Document()
    doc.add(polylines, layer_id=1)
    bounds = doc.bounds()
    if bounds is None:
        return None
    xmin, ymin, xmax, ymax = bounds

    px_per_mm = vpype.convert_length("1mm")
    if width_mm is not None:
        if xmax - xmin <= 0:
            raise ValueError(
                "la largeur du dessin détecté est nulle, "
                "impossible d'appliquer --width"
            )
        s = width_mm * px_per_mm / (xmax - xmin)
    else:
        s = 1.0
    m = margin_mm * px_per_mm

    doc.scale(s)
    doc.translate(m - xmin * s, m - ymin * s)
    doc.page_size = ((xmax - xmin) * s + 2 * m, (ymax - ymin) * s + 2 * m)
    return doc


def optimize(doc, merge_tol_mm: float, simplify_tol_mm: float):
    """Pipeline vpype : fusion des extrémités proches, rebouclage des chemins
    fermés, tri minimisant les déplacements plume levée, simplification."""
    import vpype_cli

    return vpype_cli.execute(
        f"linemerge --tolerance {merge_tol_mm}mm "
        f"reloop "
        f"linesort "
        f"linesimplify --tolerance {simplify_tol_mm}mm",
        doc,
    )


def _pen_up_length(doc) -> float:
    total = 0.0
    for layer in doc.layers.values():
        length = layer.pen_up_length()
        total += length[0] if isinstance(length, tuple) else float(length)
    return total


def _line_count(doc) -> int:
    return sum(len(layer) for layer in doc.layers.values())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="trace2svg",
        description=(
            "Convertit une image raster d'un dessin au trait monoligne en SVG "
            "centerline optimisé pour traceur à stylo (via vpype)."
        ),
        epilog=(
            "Sans --width, l'échelle reste en pixels CSS (96 px/pouce) ; les "
            "tolérances en mm restent valables (0,3 mm ≈ 1,1 px). "
            "Code de sortie : 0 succès, 1 échec ou aucun trait détecté."
        ),
    )
    p.add_argument("input", help="image raster du dessin au trait (PNG, JPG, WebP…)")
    p.add_argument(
        "-o", "--output",
        help="fichier SVG de sortie (défaut : entrée avec l'extension .svg)",
    )
    p.add_argument(
        "--width", type=float, default=None, metavar="MM",
        help="largeur physique cible du dessin en millimètres, "
             "proportions conservées (défaut : pas de mise à l'échelle)",
    )
    p.add_argument(
        "--margin", type=float, default=0.0, metavar="MM",
        help="marge de page autour du dessin en millimètres (défaut : 0)",
    )
    p.add_argument(
        "--threshold", type=int, default=None, metavar="0-255",
        help="seuil de binarisation, l'encre étant plus sombre que le seuil "
             "(défaut : automatique, méthode d'Otsu)",
    )
    p.add_argument(
        "--invert", action="store_true",
        help="inverse la binarisation, pour des traits clairs sur fond sombre",
    )
    p.add_argument(
        "--blur", type=float, default=0.0, metavar="SIGMA",
        help="flou gaussien avant seuillage, en pixels (défaut : 0, désactivé)",
    )
    p.add_argument(
        "--close", type=int, default=0, metavar="N",
        help="N itérations de fermeture morphologique 3x3 pour réparer les "
             "micro-coupures des traits (défaut : 0)",
    )
    p.add_argument(
        "--despeckle", type=int, default=9, metavar="PX2",
        help="supprime les composantes de moins de N pixels (défaut : 9)",
    )
    p.add_argument(
        "--prune", type=float, default=5.0, metavar="PX",
        help="supprime les barbules du squelette plus courtes que N pixels "
             "(défaut : 5)",
    )
    p.add_argument(
        "--min-length", type=float, default=0.0, metavar="PX",
        help="ignore les tracés plus courts que N pixels, mesurés dans "
             "l'image source (défaut : 0)",
    )
    p.add_argument(
        "--merge-tol", type=float, default=0.3, metavar="MM",
        help="tolérance de fusion des extrémités proches, en mm (défaut : 0,3)",
    )
    p.add_argument(
        "--simplify-tol", type=float, default=0.1, metavar="MM",
        help="tolérance de simplification des nœuds, en mm (défaut : 0,1)",
    )
    p.add_argument(
        "-v", "--verbose", action="store_true",
        help="affiche des statistiques de traitement sur stderr",
    )
    return p


def _err(msg: str) -> None:
    print(f"trace2svg : {msg}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out_path = Path(args.output) if args.output else Path(args.input).with_suffix(".svg")

    def info(msg: str) -> None:
        if args.verbose:
            print(f"trace2svg : {msg}", file=sys.stderr)

    try:
        gray = load_grayscale(args.input)
    except FileNotFoundError:
        _err(f"fichier introuvable : {args.input}")
        return 1
    except Exception as e:  # UnidentifiedImageError, DecompressionBombError…
        _err(f"impossible de lire l'image « {args.input} » : {e}")
        return 1

    try:
        ink, seuil = binarize(
            gray,
            threshold=args.threshold,
            invert=args.invert,
            blur=args.blur,
            close=args.close,
            despeckle=args.despeckle,
        )
        if seuil is not None:
            info(f"seuil de binarisation : {seuil:.1f}")

        ratio_encre = float(ink.mean())
        if ratio_encre > 0.5:
            _err(
                f"attention : {ratio_encre:.0%} de pixels encrés après seuillage — "
                "traits clairs sur fond sombre ? Essayez --invert."
            )

        if not ink.any():
            _err(
                "Aucun trait détecté dans l'image (essayez --invert, ajustez "
                "--threshold, ou réduisez --despeckle). Aucun fichier écrit."
            )
            return 1

        import skimage.morphology

        skel = skimage.morphology.skeletonize(ink)
        polylines, end_degrees = skeleton_to_polylines(skel)
        info(f"squelette : {int(skel.sum())} px, {len(polylines)} chaînes brutes")

        polylines = prune_spurs(polylines, end_degrees, args.prune)
        if args.min_length > 0:
            polylines = [l for l in polylines if polyline_length(l) >= args.min_length]

        if not polylines:
            _err(
                "Aucun trait détecté dans l'image (essayez --invert, ajustez "
                "--threshold, ou réduisez --despeckle). Aucun fichier écrit."
            )
            return 1

        doc = build_document(polylines, args.width, args.margin)
        if doc is None:
            _err("Aucun trait détecté dans l'image. Aucun fichier écrit.")
            return 1

        avant_traces = _line_count(doc)
        avant_plume = _pen_up_length(doc)
        doc = optimize(doc, args.merge_tol, args.simplify_tol)
        apres_traces = _line_count(doc)
        apres_plume = _pen_up_length(doc)

        import vpype

        px_per_mm = vpype.convert_length("1mm")
        page_l, page_h = doc.page_size
        info(
            f"optimisation vpype : {avant_traces} -> {apres_traces} tracés, "
            f"plume levée {avant_plume / px_per_mm:.0f} -> "
            f"{apres_plume / px_per_mm:.0f} mm"
        )
        info(f"page : {page_l / px_per_mm:.1f} x {page_h / px_per_mm:.1f} mm")

        # Écriture atomique en tout dernier : jamais de sortie partielle.
        tmp_path = out_path.with_name(out_path.name + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as fp:
            vpype.write_svg(fp, doc, color_mode="none", set_date=False)
        os.replace(tmp_path, out_path)
        info(f"écrit : {out_path}")
        return 0

    except Exception as e:
        _err(f"échec du traitement : {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
