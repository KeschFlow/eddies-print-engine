# =========================================================
# text_layout.py — E.P.E. Eddie's Print Engine — v6 LAYOUT CORE
#
# PURPOSE:
# - Clean ReportLab Paragraph wrapping (no drawString hacks)
# - Deterministic fit-check (return_fit=True) -> KDP quality gate
# - Centralized styles (KidsText / SeniorBody etc.)
#
# CONTRACT (used by app.py):
#   ok = draw_wrapped_text(
#       c, text,
#       x=<left>, y=<top>,
#       width=<w>, height=<h>,
#       style_name="KidsText" or "SeniorBody",
#       return_fit=True
#   )
#   - y is TOP edge (not bottom). This matches your app.py geometry usage.
#   - If return_fit=True: returns bool fit; never truncates.
#   - If return_fit=False: draws what fits (still no truncation, but no hard-fail).
#
# NOTE:
# - Coordinates are standard ReportLab (origin bottom-left).
# - We treat the given box as a hard bounding box.
# =========================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics


# =========================================================
# INTERNALS
# =========================================================

def _font_exists(name: str) -> bool:
    try:
        return name in pdfmetrics.getRegisteredFontNames()
    except Exception:
        return False

def _pick_font(preferred: str, fallback: str) -> str:
    return preferred if _font_exists(preferred) else fallback

# Match app.py registration names
FONT_NORMAL = _pick_font("EDDIES_FONT", "Helvetica")
FONT_BOLD   = _pick_font("EDDIES_FONT_BOLD", "Helvetica-Bold")

# Colors: keep print-safe, mostly black/gray
INK_BLACK = colors.Color(0, 0, 0)
INK_GRAY_70 = colors.Color(0.30, 0.30, 0.30)


# =========================================================
# STYLES (central)
# =========================================================

def _build_styles() -> Dict[str, ParagraphStyle]:
    """
    Styles tuned for your app.py card geometry:
      - KidsText: compact, readable at ~10–11pt
      - SeniorBody: larger, more open leading
    """
    base = getSampleStyleSheet()

    # We avoid base["BodyText"] pitfalls by creating explicit styles.
    kids = ParagraphStyle(
        name="KidsText",
        parent=base["Normal"],
        fontName=FONT_NORMAL,
        fontSize=10.5,
        leading=12.5,
        textColor=INK_BLACK,
        spaceBefore=0,
        spaceAfter=0,
        leftIndent=0,
        rightIndent=0,
        firstLineIndent=0,
        alignment=0,  # left
        allowWidows=0,
        allowOrphans=0,
        wordWrap="CJK",  # robust wrapping even with weird tokens
    )

    kids_small = ParagraphStyle(
        name="KidsSmall",
        parent=kids,
        fontSize=9.5,
        leading=11.5,
        textColor=INK_GRAY_70,
    )

    senior = ParagraphStyle(
        name="SeniorBody",
        parent=base["Normal"],
        fontName=FONT_NORMAL,
        fontSize=12.5,
        leading=15.0,
        textColor=INK_BLACK,
        spaceBefore=0,
        spaceAfter=0,
        leftIndent=0,
        rightIndent=0,
        firstLineIndent=0,
        alignment=0,
        allowWidows=0,
        allowOrphans=0,
        wordWrap="CJK",
    )

    senior_small = ParagraphStyle(
        name="SeniorSmall",
        parent=senior,
        fontSize=11.0,
        leading=13.5,
        textColor=INK_GRAY_70,
    )

    # Optional: label-ish style if you ever need it
    label = ParagraphStyle(
        name="Label",
        parent=base["Normal"],
        fontName=FONT_BOLD,
        fontSize=10.5,
        leading=12.0,
        textColor=INK_BLACK,
        spaceBefore=0,
        spaceAfter=0,
        alignment=0,
        wordWrap="CJK",
    )

    return {
        "KidsText": kids,
        "KidsSmall": kids_small,
        "SeniorBody": senior,
        "SeniorSmall": senior_small,
        "Label": label,
    }

STYLES: Dict[str, ParagraphStyle] = _build_styles()


# =========================================================
# PUBLIC API
# =========================================================

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
    debug: bool = False,
) -> bool:
    """
    Draw wrapped text inside a fixed box.

    PARAMETERS
    ----------
    c: reportlab.pdfgen.canvas.Canvas
    text: str
    x: left of box
    y: TOP of box (important!)
    width: box width
    height: box height
    style_name: key in STYLES
    return_fit: if True -> return bool fit (no drawing if not fit)
    debug: if True -> draws box outline (dev only)

    RETURNS
    -------
    bool:
      - if return_fit=True: True if text fits, False if not
      - if return_fit=False: True if drawn (best effort), False if empty text
    """
    s = (text or "").strip()
    if not s:
        return True if return_fit else False

    style = STYLES.get(style_name) or STYLES["KidsText"]

    # Optional debug box
    if debug:
        c.saveState()
        c.setStrokeColor(colors.red)
        c.setLineWidth(0.3)
        # y is top edge -> convert to bottom-left for rect
        c.rect(x, y - height, width, height, stroke=1, fill=0)
        c.restoreState()

    # Paragraph supports a subset of HTML-like markup; escape is user's job.
    # We keep it plain text by default.
    para = Paragraph(s, style)

    # Wrap measures required height for given width
    w, h = para.wrap(width, height)

    # If doesn't fit, decide behavior
    if h > height + 1e-6:
        if return_fit:
            return False
        # Non-hard mode: draw nothing (never truncate) but signal failure
        return False

    # Draw: Para.drawOn expects bottom-left
    bottom_y = y - h
    para.drawOn(c, x, bottom_y)
    return True


# =========================================================
# OPTIONAL: Convenience helper for strict mode
# =========================================================

def assert_wrapped_text_fits(
    c,
    text: str,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    style_name: str = "KidsText",
    label: str = "text",
) -> None:
    """
    Strict variant: raises ValueError if text doesn't fit.
    Useful if you ever want to keep the gate centralized here.
    """
    ok = draw_wrapped_text(
        c,
        text,
        x=x, y=y, width=width, height=height,
        style_name=style_name,
        return_fit=True,
    )
    if not ok:
        raise ValueError(f"OVERFLOW: {label} does not fit ({style_name})")
