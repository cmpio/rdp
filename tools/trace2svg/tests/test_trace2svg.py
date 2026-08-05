"""Tests de trace2svg — images synthétiques PIL générées dans tmp_path.

T1 est la preuve quantitative du traçage centerline : un cercle de rayon r
tracé au trait de 3 px doit produire UNE polyligne de longueur ~ 2*pi*r ;
un vectoriseur par contours (type potrace) donnerait deux anneaux, soit
~ 4*pi*r — un ratio de 2, très au-delà de la bande d'acceptation.
"""

import math
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import trace2svg  # noqa: E402

SCRIPT = Path(__file__).resolve().parents[1] / "trace2svg.py"


def total_length(doc) -> float:
    return sum(
        trace2svg.polyline_length(line)
        for layer in doc.layers.values()
        for line in layer
    )


def run_pipeline(img: Image.Image, prune: float = 5.0):
    """Pipeline complet en mémoire jusqu'au Document optimisé (sans échelle)."""
    import skimage.morphology

    gray = np.asarray(img.convert("L"), dtype=np.uint8)
    ink, _ = trace2svg.binarize(gray)
    skel = skimage.morphology.skeletonize(ink)
    lines, degs = trace2svg.skeleton_to_polylines(skel)
    lines = trace2svg.prune_spurs(lines, degs, prune)
    doc = trace2svg.build_document(lines, None, 0.0)
    return trace2svg.optimize(doc, 0.3, 0.1)


def circle_image() -> Image.Image:
    img = Image.new("L", (300, 300), 255)
    d = ImageDraw.Draw(img)
    d.ellipse((50, 50, 250, 250), outline=0, width=3)
    return img


def doodle_image() -> Image.Image:
    """Portrait synthétique : lunettes (2 cercles + pont), arc de tête
    croisant les branches (jonctions), nez, bouche — traits de 3 px."""
    img = Image.new("L", (400, 400), 255)
    d = ImageDraw.Draw(img)
    d.ellipse((75, 115, 165, 205), outline=0, width=3)
    d.ellipse((235, 115, 325, 205), outline=0, width=3)
    d.line((165, 160, 235, 160), fill=0, width=3)
    d.line((75, 160, 40, 150), fill=0, width=3)
    d.line((325, 160, 360, 150), fill=0, width=3)
    d.arc((40, 40, 360, 280), 180, 360, fill=0, width=3)
    d.line((200, 180, 195, 220, 210, 225), fill=0, width=3)
    d.arc((175, 235, 225, 265), 0, 180, fill=0, width=3)
    return img


def read_svg_doc(path: Path):
    import vpype_cli

    return vpype_cli.execute(f'read "{path}"')


# ---------------------------------------------------------------- T1
def test_centerline_circle():
    doc = run_pipeline(circle_image())
    lines = [line for layer in doc.layers.values() for line in layer]
    assert len(lines) == 1, "le cercle doit fusionner en un seul tracé"
    total = total_length(doc)
    attendu = 2 * math.pi * 100
    assert 0.90 * attendu <= total <= 1.15 * attendu, (
        f"longueur {total:.0f} hors bande centerline "
        f"(un contour doublé donnerait ~{2 * attendu:.0f})"
    )
    assert abs(lines[0][0] - lines[0][-1]) < 2.0, "le cercle doit rester fermé"


def test_polylines_sont_complexes_1d():
    import skimage.morphology

    ink, _ = trace2svg.binarize(np.asarray(circle_image(), dtype=np.uint8))
    lines, _ = trace2svg.skeleton_to_polylines(skimage.morphology.skeletonize(ink))
    assert lines, "au moins une polyligne attendue"
    for line in lines:
        # vpype corrompt silencieusement tout ce qui n'est pas complexe 1D
        assert line.ndim == 1 and np.iscomplexobj(line)


# ---------------------------------------------------------------- T2
def test_portrait_synthetique(tmp_path):
    src = tmp_path / "doodle.png"
    out = tmp_path / "doodle.svg"
    doodle_image().save(src)
    rc = trace2svg.main([str(src), "-o", str(out)])
    assert rc == 0
    assert out.exists()
    root = ET.parse(out).getroot()
    assert root.tag.endswith("svg")
    n = sum(len(layer) for layer in read_svg_doc(out).layers.values())
    assert 2 <= n <= 25, f"{n} tracés : hors de la plage attendue"


# ---------------------------------------------------------------- T3
def test_invert(tmp_path, capsys):
    normal, inverse = tmp_path / "n.png", tmp_path / "i.png"
    doodle_image().save(normal)
    ImageOps.invert(doodle_image()).save(inverse)

    out_n, out_i = tmp_path / "n.svg", tmp_path / "i.svg"
    assert trace2svg.main([str(normal), "-o", str(out_n)]) == 0
    assert trace2svg.main([str(inverse), "-o", str(out_i), "--invert"]) == 0
    ln = total_length(read_svg_doc(out_n))
    li = total_length(read_svg_doc(out_i))
    assert abs(ln - li) / ln < 0.05, "géométrie identique attendue à 5 % près"

    # Sans --invert : l'avertissement doit suggérer le bon remède.
    capsys.readouterr()
    rc = trace2svg.main([str(inverse), "-o", str(tmp_path / "w.svg")])
    assert rc == 0
    assert "--invert" in capsys.readouterr().err


# ---------------------------------------------------------------- T4
@pytest.mark.parametrize("valeur", [255, 0], ids=["blanche", "noire"])
def test_image_sans_trait(tmp_path, capsys, valeur):
    src = tmp_path / "vide.png"
    out = tmp_path / "vide.svg"
    Image.new("L", (400, 400), valeur).save(src)
    rc = trace2svg.main([str(src), "-o", str(out)])
    assert rc == 1
    assert "Aucun trait" in capsys.readouterr().err
    assert not out.exists()


# ---------------------------------------------------------------- T5
def test_despeckle():
    img = Image.new("L", (400, 400), 255)
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(42)
    for _ in range(40):
        x, y = int(rng.integers(10, 390)), int(rng.integers(10, 390))
        if abs(y - 200) < 10:  # éviter le segment de référence
            continue
        w, h = int(rng.integers(1, 3)), int(rng.integers(1, 3))
        d.rectangle((x, y, x + w - 1, y + h - 1), fill=0)
    d.line((100, 200, 300, 200), fill=0, width=3)

    doc = run_pipeline(img)
    lines = [line for layer in doc.layers.values() for line in layer]
    assert len(lines) == 1, "les mouchetures doivent disparaître"
    assert 0.9 * 200 <= total_length(doc) <= 1.1 * 200


# ---------------------------------------------------------------- T6
def test_echelle_physique(tmp_path):
    src = tmp_path / "cercle.png"
    out = tmp_path / "cercle.svg"
    circle_image().save(src)
    rc = trace2svg.main([str(src), "-o", str(out), "--width", "100", "--margin", "0"])
    assert rc == 0

    root = ET.parse(out).getroot()
    largeur_cm = float(re.fullmatch(r"([\d.]+)cm", root.get("width")).group(1))
    assert largeur_cm == pytest.approx(10.0, rel=1e-3), "bbox = 100 mm attendu"

    vb = [float(v) for v in root.get("viewBox").split()]
    assert vb[2] == pytest.approx(100 * 96 / 25.4, rel=1e-3)
    # cercle : boîte englobante carrée, proportions conservées
    assert vb[3] / vb[2] == pytest.approx(1.0, abs=0.02)


# ---------------------------------------------------------------- T7
def test_gain_linesort():
    # 14 traits verticaux disjoints, ordre adversarial alternant gauche/droite :
    # le tri doit réduire la plume levée d'au moins 40 %.
    lignes = []
    for k in range(14):
        x = 30.0 if k % 2 == 0 else 370.0
        y = 10.0 + 25.0 * k
        lignes.append(np.array([x + 1j * y, x + 1j * (y + 80.0)]))
    doc = trace2svg.build_document(lignes, None, 0.0)
    avant = trace2svg._pen_up_length(doc)
    doc = trace2svg.optimize(doc, 0.3, 0.1)
    apres = trace2svg._pen_up_length(doc)
    assert apres < 0.6 * avant


# ---------------------------------------------------------------- T8
def test_prune_spurs():
    longue = np.array([0 + 0j, 100 + 0j])
    barbule = np.array([50 + 0j, 50 + 3j])
    isolee = np.array([200 + 0j, 203 + 0j])
    boucle = np.array([0 + 10j, 3 + 10j, 3 + 13j, 0 + 10j])
    lignes = [longue, barbule, isolee, boucle]
    degres = [(1, 3), (3, 1), (1, 1), (2, 2)]

    avec = trace2svg.prune_spurs(lignes, degres, 5.0)
    sans = trace2svg.prune_spurs(lignes, degres, 0.0)
    assert len(sans) == 4
    assert len(avec) == 3, "seule la barbule jonction->pointe doit disparaître"
    assert not any(l is barbule for l in avec)


# ---------------------------------------------------------------- smoke CLI
def test_cli_sans_traceback(tmp_path):
    src = tmp_path / "vide.png"
    Image.new("L", (100, 100), 255).save(src)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(src)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1
    assert "Aucun trait" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_cli_fichier_introuvable(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path / "absent.png")],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1
    assert "introuvable" in proc.stderr
    assert "Traceback" not in proc.stderr
