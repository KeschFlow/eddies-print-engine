# kern/pdf_engine.py
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Optional

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

# Branding-Farbe (zentral definiert)
EDDIE_PURPLE = colors.HexColor("#7c3aed")


@dataclass(frozen=True)
class PageSpec:
    page_w: float
    page_h: float
    bleed: float
    safe: float  # Abstand vom Trim-Rand (inkl. Bleed)


def get_page_spec(*, kdp_mode: bool, square: bool = True) -> PageSpec:
    """
    KDP Print:
      - Trim: 8.5" x 8.5" (square=True) oder A4 (square=False)
      - Bleed: 0.125" rundum
      - Safe Zone: bleed + 0.375"
    Dev/Preview:
      - Kein Bleed, safe = 0.5"
    """
    if kdp_mode:
        bleed = 0.125 * inch
        if square:
            trim_size = 8.5 * inch
            page_w = page_h = trim_size + 2 * bleed
        else:
            page_w = 8.27 * inch + 2 * bleed
            page_h = 11.69 * inch + 2 * bleed
        safe = bleed + 0.375 * inch
    else:
        bleed = 0.0
        if square:
            page_w = page_h = 8.5 * inch
        else:
            page_w = 8.27 * inch
            page_h = 11.69 * inch
        safe = 0.5 * inch

    return PageSpec(page_w=float(page_w), page_h=float(page_h), bleed=bleed, safe=safe)


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
    title_font: str = "Helvetica-Bold",
    title_size: int = 12,
    padding: float = 8,
):
    """Zeichnet eine Box (x,y ist links-unten)."""
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
    scale_to: float = 0.75,
    debug_on_error: bool = False,
):
    """
    Bettet ein Bild (BytesIO) zentriert und skaliert ein.
    RAM-only, EXIF-Rotation, RGB-Konvertierung, Error-Fallback.
    """
    try:
        from PIL import Image, ImageOps

        img_data.seek(0)
        im = Image.open(img_data)
        im = ImageOps.exif_transpose(im)

        if im.mode != "RGB":
            im = im.convert("RGB")

        img_w, img_h = im.size
        if img_w <= 0 or img_h <= 0:
            raise ValueError("Ungültige Bilddimensionen")

        target_w = max_w * float(scale_to)
        target_h = max_h * float(scale_to)

        if preserve_aspect:
            scale = min(target_w / img_w, target_h / img_h)
            draw_w = img_w * scale
            draw_h = img_h * scale
        else:
            draw_w, draw_h = target_w, target_h

        dx = (max_w - draw_w) / 2
        dy = (max_h - draw_h) / 2

        c.drawImage(ImageReader(im), x + dx, y + dy, width=draw_w, height=draw_h, mask="auto")

    except Exception as e:
        if debug_on_error:
            c.saveState()
            c.setFont("Helvetica", 10)
            c.setFillColor(colors.red)
            c.drawString(x + 12, y + 12, f"Bild-Fehler: {str(e)[:80]}")
            c.restoreState()


# =========================================================
# Hilfsfunktionen für Icons
# =========================================================

def _icon_style(c: canvas.Canvas, size: float):
    """Einheitlicher Stil für alle Icons: schwarze Linien, variable Stärke"""
    c.setStrokeColor(colors.black)
    c.setLineWidth(max(1, size * 0.04))
    c.setFillColor(colors.black)


def _draw_purple_dot(c: canvas.Canvas, x: float, y: float, r: float):
    """Kleiner lila Akzent-Punkt (wird oft als Highlight verwendet)"""
    c.setFillColor(EDDIE_PURPLE)
    c.circle(x, y, r, fill=1, stroke=0)


# =========================================================
# Bestehende Icon-Funktionen (bereits vorhanden)
# =========================================================

def draw_icon_hammer(c: canvas.Canvas, cx: float, cy: float, size: float):
    c.saveState()
    _icon_style(c, size)
    c.line(cx - size*0.4, cy - size*0.4, cx + size*0.4, cy + size*0.4)
    c.rect(cx + size*0.25, cy + size*0.25, size*0.5, size*0.15, fill=1, stroke=1)
    _draw_purple_dot(c, cx + size*0.5, cy + size*0.5, size*0.08)
    c.restoreState()


def draw_icon_wrench(c: canvas.Canvas, cx: float, cy: float, size: float):
    c.saveState()
    _icon_style(c, size)
    c.line(cx - size*0.45, cy - size*0.45, cx + size*0.45, cy + size*0.45)
    c.arc(cx + size*0.3, cy + size*0.3, size*0.5, 30, 330)
    _draw_purple_dot(c, cx + size*0.6, cy + size*0.6, size*0.07)
    c.restoreState()


def draw_icon_gear(c: canvas.Canvas, cx: float, cy: float, size: float):
    c.saveState()
    _icon_style(c, size)
    c.circle(cx, cy, size*0.4, fill=0, stroke=1)
    for angle in range(0, 360, 45):
        from math import cos, sin, radians
        x1 = cx + size*0.4 * cos(radians(angle))
        y1 = cy + size*0.4 * sin(radians(angle))
        x2 = cx + size*0.55 * cos(radians(angle))
        y2 = cy + size*0.55 * sin(radians(angle))
        c.line(x1, y1, x2, y2)
    _draw_purple_dot(c, cx, cy, size*0.08)
    c.restoreState()


def draw_icon_medical_cross(c: canvas.Canvas, cx: float, cy: float, size: float):
    c.saveState()
    _icon_style(c, size)
    c.rect(cx - size*0.15, cy - size*0.4, size*0.3, size*0.8, fill=1, stroke=0)
    c.rect(cx - size*0.4, cy - size*0.15, size*0.8, size*0.3, fill=1, stroke=0)
    c.restoreState()


def draw_icon_briefcase(c: canvas.Canvas, cx: float, cy: float, size: float):
    c.saveState()
    _icon_style(c, size)
    c.rect(cx - size*0.45, cy - size*0.3, size*0.9, size*0.6, fill=0, stroke=1)
    c.rect(cx - size*0.15, cy + size*0.2, size*0.3, size*0.15, fill=0, stroke=1)
    _draw_purple_dot(c, cx + size*0.4, cy, size*0.06)
    c.restoreState()


def draw_icon_book_open(c: canvas.Canvas, cx: float, cy: float, size: float):
    c.saveState()
    _icon_style(c, size)
    c.rect(cx - size*0.45, cy - size*0.35, size*0.4, size*0.7, fill=0, stroke=1)
    c.rect(cx + size*0.05, cy - size*0.35, size*0.4, size*0.7, fill=0, stroke=1)
    c.line(cx, cy - size*0.35, cx, cy + size*0.35)
    _draw_purple_dot(c, cx, cy + size*0.45, size*0.06)
    c.restoreState()


def draw_icon_fork_knife(c: canvas.Canvas, cx: float, cy: float, size: float):
    c.saveState()
    _icon_style(c, size)
    c.line(cx - size*0.3, cy - size*0.5, cx - size*0.3, cy + size*0.5)
    c.line(cx - size*0.4, cy + size*0.4, cx - size*0.2, cy + size*0.4)
    c.setFillColor(EDDIE_PURPLE)
    c.circle(cx + size*0.3, cy + size*0.5, size*0.06, fill=1, stroke=0)
    c.restoreState()


def draw_icon_computer(c: canvas.Canvas, cx: float, cy: float, size: float):
    c.saveState()
    _icon_style(c, size)
    c.rect(cx - size*0.45, cy - size*0.35, size*0.9, size*0.7, fill=0, stroke=1)
    c.rect(cx - size*0.35, cy - size*0.45, size*0.7, size*0.1, fill=0, stroke=1)
    _draw_purple_dot(c, cx + size*0.4, cy + size*0.1, size*0.06)
    c.restoreState()


# =========================================================
# NEUE Icon-Funktionen (für fehlende Slugs)
# =========================================================

def draw_icon_scissors(c: canvas.Canvas, cx: float, cy: float, size: float):
    """Schere (für Schneidern)"""
    c.saveState()
    _icon_style(c, size)
    c.line(cx - size*0.5, cy - size*0.4, cx + size*0.5, cy + size*0.4)
    c.line(cx - size*0.5, cy + size*0.4, cx + size*0.5, cy - size*0.4)
    c.line(cx, cy - size*0.4, cx, cy + size*0.4)
    _draw_purple_dot(c, cx, cy, size*0.08)
    c.restoreState()


def draw_icon_syringe(c: canvas.Canvas, cx: float, cy: float, size: float):
    """Spritze (für Pflege)"""
    c.saveState()
    _icon_style(c, size)
    # Kanüle
    c.line(cx - size*0.5, cy, cx + size*0.5, cy)
    # Kolben
    c.rect(cx - size*0.1, cy - size*0.2, size*0.2, size*0.4, fill=0, stroke=1)
    # Griff
    c.rect(cx + size*0.3, cy - size*0.15, size*0.2, size*0.3, fill=0, stroke=1)
    _draw_purple_dot(c, cx + size*0.4, cy, size*0.06)
    c.restoreState()


def draw_icon_envelope(c: canvas.Canvas, cx: float, cy: float, size: float):
    """Briefumschlag (für E-Mail/Kommunikation)"""
    c.saveState()
    _icon_style(c, size)
    c.line(cx - size*0.5, cy + size*0.3, cx + size*0.5, cy + size*0.3)
    c.line(cx - size*0.5, cy + size*0.3, cx, cy - size*0.3)
    c.line(cx + size*0.5, cy + size*0.3, cx, cy - size*0.3)
    _draw_purple_dot(c, cx, cy, size*0.07)
    c.restoreState()


def draw_icon_calendar(c: canvas.Canvas, cx: float, cy: float, size: float):
    """Kalender (für Termine)"""
    c.saveState()
    _icon_style(c, size)
    c.rect(cx - size*0.45, cy - size*0.45, size*0.9, size*0.9, fill=0, stroke=1)
    c.rect(cx - size*0.45, cy + size*0.15, size*0.9, size*0.3, fill=1, stroke=0)
    _draw_purple_dot(c, cx, cy - size*0.1, size*0.08)
    c.restoreState()


def draw_icon_wheelchair(c: canvas.Canvas, cx: float, cy: float, size: float):
    """Rollstuhl (für Pflege)"""
    c.saveState()
    _icon_style(c, size)
    c.circle(cx - size*0.3, cy - size*0.3, size*0.2, fill=0, stroke=1)
    c.circle(cx + size*0.3, cy - size*0.3, size*0.2, fill=0, stroke=1)
    c.rect(cx - size*0.4, cy - size*0.1, size*0.8, size*0.4, fill=0, stroke=1)
    _draw_purple_dot(c, cx, cy + size*0.1, size*0.07)
    c.restoreState()


def draw_icon_tray(c: canvas.Canvas, cx: float, cy: float, size: float):
    """Tablett (für Kellner/Gastronomie)"""
    c.saveState()
    _icon_style(c, size)
    c.rect(cx - size*0.5, cy - size*0.4, size*1.0, size*0.3, fill=0, stroke=1)
    c.line(cx - size*0.5, cy - size*0.1, cx + size*0.5, cy - size*0.1)
    _draw_purple_dot(c, cx, cy + size*0.1, size*0.08)
    c.restoreState()
