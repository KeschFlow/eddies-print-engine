# text_layout.py
# ReportLab Paragraph-based wrapping for KDP-safe text layout

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT


@dataclass(frozen=True)
class _StyleSpec:
    fontName: str
    fontSize: float
    leading: float


def _build_styles() -> Dict[str, ParagraphStyle]:
    ss = getSampleStyleSheet()

    # Safe defaults: DejaVu/Helvetica already registered in app.py; Paragraph uses fontName string.
    # If "EDDIES_FONT" exists it will render; otherwise ReportLab falls back if it can't find it.
    base = ParagraphStyle(
        "Base",
        parent=ss["Normal"],
        fontName="EDDIES_FONT",
        fontSize=10,
        leading=12,
        alignment=TA_LEFT,
        spaceBefore=0,
        spaceAfter=0,
    )

    kids = ParagraphStyle("KidsText", parent=base, fontName="EDDIES_FONT", fontSize=10, leading=12)
    tiny = ParagraphStyle("Tiny", parent=base, fontName="EDDIES_FONT", fontSize=8, leading=10)

    senior = ParagraphStyle("SeniorBody", parent=base, fontName="EDDIES_FONT", fontSize=12, leading=15)
    senior_tiny = ParagraphStyle("SeniorTiny", parent=base, fontName="EDDIES_FONT", fontSize=10, leading=12)

    # Labels are mostly drawn via drawString in app.py, but available if you want them later
    kids_label = ParagraphStyle("KidsLabel", parent=base, fontName="EDDIES_FONT", fontSize=10, leading=12)
    senior_label = ParagraphStyle("SeniorLabel", parent=base, fontName="EDDIES_FONT", fontSize=12, leading=15)

    return {
        "Base": base,
        "KidsText": kids,
        "Tiny": tiny,
        "SeniorBody": senior,
        "SeniorTiny": senior_tiny,
        "KidsLabel": kids_label,
        "SeniorLabel": senior_label,
    }


_STYLES = _build_styles()


def draw_wrapped_text(
    c,
    text: str,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    style_name: str = "KidsText",
    return_fit: bool = False,
) -> bool | None:
    """
    Draw a Paragraph inside a top-left anchored box:
      - (x, y) is TOP-left of the box
      - width/height are box dimensions
    Returns:
      - None by default
      - bool fit status if return_fit=True
    """
    t = (text or "").strip()
    if not t:
        return (True if return_fit else None)

    style = _STYLES.get(style_name) or _STYLES["Base"]

    # Simple sanitization (ReportLab Paragraph parses basic HTML-like tags)
    t = (
        t.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )

    p = Paragraph(t, style=style)
    w, h = p.wrap(width, height)

    fit = (h <= height + 0.001)  # float tolerance
    # Paragraph.drawOn uses bottom-left origin; convert from top-left box
    p.drawOn(c, x, y - h)

    return (fit if return_fit else None)
