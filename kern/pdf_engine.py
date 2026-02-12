# kern/pdf_engine.py
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Optional

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader


@dataclass(frozen=True)
class PageSpec:
    page_w: float
    page_h: float
    bleed: float
    safe: float  # "safe zone" Abstand vom Rand (inkl. bleed)


def get_page_spec(*, kdp_mode: bool) -> PageSpec:
    """
    KDP: 8.5"x8.5" + 0.125" bleed rundum.
    Safe Zone: mind. 0.375" vom trim-Rand (also bleed + 0.375").
    """
    bleed = 0.125 * inch if kdp_mode else 0.0
    page_w = 8.5 * inch + 2 * bleed if kdp_mode else (8.27 * inch)  # ~A4 Breite in inch
    page_h = 8.5 * inch + 2 * bleed if kdp_mode else (11.69 * inch)  # ~A4 Höhe in inch
    safe = (bleed + 0.375 * inch) if kdp_mode else (0.5 * inch)
    return PageSpec(page_w=page_w, page_h=page_h, bleed=bleed, safe=safe)


def draw_box(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    title: Optional[str] = None,
    stroke=colors.black,
    fill=None,
    title_font="Helvetica-Bold",
    title_size=12,
    padding: float = 8,
):
    c.saveState()
    c.setLineWidth(1)
    c.setStrokeColor(stroke)
    if fill is not None:
        c.setFillColor(fill)
        c.rect(x, y, w, h, fill=1, stroke=1)
    else:
        c.rect(x, y, w, h, fill=0, stroke=1)

    if title:
        c.setFont(title_font, title_size)
        c.setFillColor(colors.black)
        c.drawString(x + padding, y + h - title_size - padding / 2, title)

    c.restoreState()


def embed_image(
    c: canvas.Canvas,
    *,
    img_data: io.BytesIO,
    x: float,
    y: float,
    max_w: float,
    max_h: float,
    preserve_aspect: bool = True,
    scale_to: float = 0.5,
    debug_on_error: bool = False,
):
    """
    Einbettet ein Bild (BytesIO) in eine Box:
    - RAM-only: nutzt BytesIO, speichert nichts.
    - Auto-Rotation via EXIF.
    - Zentriert und skaliert (standard: max 50% der Box).
    """
    try:
        from PIL import Image, ImageOps

        img_data.seek(0)
        im = Image.open(img_data)

        # EXIF Auto-Rotation (wichtig bei Handyfotos)
        im = ImageOps.exif_transpose(im)

        # ReportLab mag RGB/Gray – wir normalisieren auf RGB
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        elif im.mode == "L":
            im = im.convert("RGB")

        img_w, img_h = im.size
        if img_w <= 0 or img_h <= 0:
            raise ValueError("Ungültige Bilddimensionen.")

        # Skalierung: default nur bis 50% der Box, um Layout zu halten
        target_w = max_w * float(scale_to)
        target_h = max_h * float(scale_to)

        if preserve_aspect:
            scale = min(target_w / img_w, target_h / img_h)
            draw_w = img_w * scale
            draw_h = img_h * scale
        else:
            draw_w = target_w
            draw_h = target_h

        # Zentrieren innerhalb der übergebenen Box
        dx = (max_w - draw_w) / 2
        dy = (max_h - draw_h) / 2

        # ImageReader akzeptiert PIL Image direkt (robuster als drawInlineImage(BytesIO))
        c.drawImage(ImageReader(im), x + dx, y + dy, width=draw_w, height=draw_h, mask="auto")

    except Exception as e:
        if debug_on_error:
            c.saveState()
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.red)
            c.drawString(x + 8, y + 8, f"Bild-Fehler: {str(e)[:90]}")
            c.restoreState()
        # Silent-Fallback: Box bleibt leer
        return
