#!/usr/bin/env python3
"""Génère portrait_demo.png (dessin monoligne synthétique, reproductible à
l'identique) puis lance trace2svg dessus pour produire portrait_demo.svg,
commité comme référence du comportement attendu :

    python3 make_example.py
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import trace2svg  # noqa: E402

HERE = Path(__file__).resolve().parent


def dessine_portrait() -> Image.Image:
    """Petit portrait stylisé : tête, lunettes, nez, bouche — traits de 3 px."""
    img = Image.new("L", (400, 400), 255)
    d = ImageDraw.Draw(img)
    d.ellipse((75, 115, 165, 205), outline=0, width=3)   # verre gauche
    d.ellipse((235, 115, 325, 205), outline=0, width=3)  # verre droit
    d.line((165, 160, 235, 160), fill=0, width=3)        # pont
    d.line((75, 160, 40, 150), fill=0, width=3)          # branche gauche
    d.line((325, 160, 360, 150), fill=0, width=3)        # branche droite
    d.arc((40, 40, 360, 280), 180, 360, fill=0, width=3)  # crâne
    d.line((200, 180, 195, 220, 210, 225), fill=0, width=3)  # nez
    d.arc((175, 235, 225, 265), 0, 180, fill=0, width=3)  # bouche
    return img


def main() -> int:
    png = HERE / "portrait_demo.png"
    svg = HERE / "portrait_demo.svg"
    dessine_portrait().save(png)
    return trace2svg.main([str(png), "-o", str(svg), "--width", "100", "--margin", "5", "-v"])


if __name__ == "__main__":
    sys.exit(main())
