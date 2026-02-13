# kern/exports/trainer_cards.py
from __future__ import annotations

import io
from typing import Dict, Any, List, Optional, Tuple

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

from kern.pdf_engine import (
    get_page_spec,
    draw_box,
    draw_brand_mark,
    draw_icon,
)

# qrcode ist optional (Streamlit Cloud / requirements können variieren)
try:
    import qrcode  # type: ignore
except Exception:  # pragma: no cover
    qrcode = None


# -----------------------------
# Policy (6er Grid, A4)
# -----------------------------
CARDS_POLICY: Dict[str, Any] = {
    "cols": 2,
    "rows": 3,
    "outer_margin_mm": 12,
    "gap_mm": 6,
    "radius_mm": 0,  # aktuell nicht genutzt (ReportLab rect ist eckig)
    "watermark_opacity": 0.05,

    # Vorderseite
    "front_word_font_size": 20,
    "front_label_font_size": 9,
    "front_icon_ratio": 0.42,  # Anteil der Kartenhöhe für Icon-Zone

    # Rückseite
    "back_title_font_size": 12,
    "back_text_font_size": 11,
    "back_qr_ratio": 0.46,     # Anteil der Kartenhöhe für QR-Zone
    "back_qr_border": True,
    "qr_box_pad_mm": 4,

    # Schneidemarken
    "crop_mark_len_mm": 4,
    "crop_mark_offset_mm": 2,
    "crop_mark_line_width": 0.7,
}


# -----------------------------
# Helpers: Daten lesen
# -----------------------------
def _coerce_vocab(data: Dict[str, Any]) -> List[Dict[str, str]]:
    vocab = data.get("vocab")
    if isinstance(vocab, list) and vocab:
        out: List[Dict[str, str]] = []
        for it in vocab:
            if isinstance(it, dict):
                out.append(
                    {
                        "word": str(it.get("word", "")).strip(),
                        "translation": str(it.get("translation", "")).strip(),
                    }
                )
        return [v for v in out if v["word"] or v["translation"]]

    # legacy fallback
    items = data.get("items")
    if isinstance(items, list) and items:
        out2: List[Dict[str, str]] = []
        for it in items:
            if isinstance(it, dict):
                out2.append({"word": str(it.get("term", "")).strip(), "translation": ""})
        return [v for v in out2 if v["word"]]
    return []


def _build_legacy_lookup(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    items = data.get("items")
    if not isinstance(items, list):
        return lookup
    for it in items:
        if not isinstance(it, dict):
            continue
        term = str(it.get("term", "")).strip()
        if term:
            lookup[term] = it
    return lookup


def _choose_icon_slug(subject: str, word: str, legacy_icon_slug: Optional[str] = None) -> str:
    if legacy_icon_slug:
        s = str(legacy_icon_slug).strip()
        if s:
            return s

    s = (subject or "").strip().lower()
    w = (word or "").strip().lower()

    if any(k in s for k in ["pflege", "medizin", "arzt", "kranken", "hospital"]):
        return "medical_cross"
    if any(k in s for k in ["gastro", "küche", "restaurant", "service", "hotel"]):
        return "fork_knife"
    if any(k in s for k in ["bau", "handwerk", "werk", "metall", "schweiß", "schrein"]):
        return "tools"
    if "hammer" in w or "hammer" in s:
        return "hammer"
    return "briefcase"


def _pick_example_for_word(word_item: Dict[str, str], legacy: Dict[str, Any]) -> str:
    # Priorität:
    # 1) trainer_v2: item["examples"] (falls später ergänzt)
    # 2) legacy: legacy["examples"]
    v2_examples = word_item.get("examples") if isinstance(word_item, dict) else None
    if isinstance(v2_examples, list) and v2_examples:
        for s in v2_examples:
            s2 = str(s).strip()
            if s2:
                return s2

    legacy_examples = legacy.get("examples") if isinstance(legacy, dict) else None
    if isinstance(legacy_examples, list) and legacy_examples:
        for s in legacy_examples:
            s2 = str(s).strip()
            if s2:
                return s2

    # Fallback offline (ohne KI)
    w = str(word_item.get("word", "")).strip()
    return f"Ich übe das Wort: {w}."


def _make_qr_image_bytes(payload: str) -> Optional[bytes]:
    """
    Returns PNG bytes if qrcode is available, else None (offline-safe fallback).
    """
    if qrcode is None:
        return None

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    bio = io.BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()


def _draw_qr_fallback(
    c: canvas.Canvas,
    *,
    x: float,
    y: float,
    w: float,
    h: float,
    payload: str,
) -> None:
    """
    Fallback wenn qrcode nicht installiert ist: stiller Placeholder, kein Crash.
    """
    c.saveState()
    c.setStrokeColor(colors.Color(0, 0, 0, alpha=0.35))
    c.setLineWidth(1)
    c.rect(x, y, w, h, stroke=1, fill=0)

    # große "QR"
    c.setFillColor(colors.Color(0, 0, 0, alpha=0.35))
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(x + w / 2, y + h / 2 + 6, "QR")

    # Hinweis klein
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.Color(0, 0, 0, alpha=0.55))
    c.drawCentredString(x + w / 2, y + 6, "qrcode nicht installiert")

    # Payload (sehr kurz)
    short = payload.replace("\n", " • ").strip()
    if len(short) > 40:
        short = short[:37] + "..."
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.Color(0, 0, 0, alpha=0.45))
    c.drawCentredString(x + w / 2, y + 16, short)

    c.restoreState()


def _draw_crop_marks(c: canvas.Canvas, *, x: float, y: float, w: float, h: float, pol: Dict[str, Any]) -> None:
    """
    Schneidemarken an den 4 Ecken einer Karte.
    (x,y) ist unten-links der Karte.
    """
    L = float(pol["crop_mark_len_mm"]) * mm
    off = float(pol["crop_mark_offset_mm"]) * mm

    c.saveState()
    c.setStrokeColor(colors.black)
    c.setLineWidth(float(pol["crop_mark_line_width"]))

    # unten-links
    c.line(x - off, y, x - off + L, y)
    c.line(x, y - off, x, y - off + L)

    # unten-rechts
    c.line(x + w + off - L, y, x + w + off, y)
    c.line(x + w, y - off, x + w, y - off + L)

    # oben-links
    c.line(x - off, y + h, x - off + L, y + h)
    c.line(x, y + h + off - L, x, y + h + off)

    # oben-rechts
    c.line(x + w + off - L, y + h, x + w + off, y + h)
    c.line(x + w, y + h + off - L, x + w, y + h + off)

    c.restoreState()


def export_trainer_cards(
    data: Dict[str, Any],
    *,
    title: str = "Eddie – QR Lernkarten",
    subtitle: Optional[str] = None,
    watermark: bool = True,
    policy: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    QR-Lernkarten (A4):
    - 6er Grid (2x3)
    - pro Batch 6 Karten:
        Seite 1 = Vorderseiten (Icon + Wort)
        Seite 2 = Rückseiten  (Beispielsatz + QR mit offline Text)
    - QR enthält reinen Text: "Wort\\nSatz" (offline lesbar)
    """
    if not isinstance(data, dict):
        raise ValueError("export_trainer_cards: data must be a dict")

    pol = dict(CARDS_POLICY)
    if policy:
        pol.update(policy)

    spec = get_page_spec("A4 Arbeitsblatt")
    page_w, page_h = spec["pagesize"]

    subject = str((data.get("subject") or "")).strip()
    vocab = _coerce_vocab(data)
    legacy_lookup = _build_legacy_lookup(data)

    if not vocab:
        vocab = [{"word": "", "translation": ""}]

    cols = int(pol["cols"])
    rows = int(pol["rows"])
    per_page = cols * rows

    outer_m = float(pol["outer_margin_mm"]) * mm
    gap = float(pol["gap_mm"]) * mm

    usable_w = page_w - 2 * outer_m
    usable_h = page_h - 2 * outer_m

    card_w = (usable_w - (cols - 1) * gap) / cols
    card_h = (usable_h - (rows - 1) * gap) / rows

    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(page_w, page_h))

    def card_xy(index_in_page: int) -> Tuple[float, float]:
        r = index_in_page // cols
        col = index_in_page % cols
        x = outer_m + col * (card_w + gap)
        y = page_h - outer_m - (r + 1) * card_h - r * gap
        return x, y

    # ---- render batches ----
    total = len(vocab)
    start = 0
    while start < total:
        batch = vocab[start: start + per_page]

        # =========================
        # FRONT PAGE (Icon + Wort)
        # =========================
        if watermark:
            draw_brand_mark(c, page_w, page_h, mode="watermark", opacity=float(pol["watermark_opacity"]))

        # Header klein
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(outer_m, page_h - outer_m + 2 * mm, title)
        c.setFont("Helvetica", 10)
        meta = subtitle or (f"Fach: {subject}" if subject else "Lernkarten")
        c.setFillColor(colors.grey)
        c.drawRightString(page_w - outer_m, page_h - outer_m + 2 * mm, meta)
        c.setFillColor(colors.black)

        for i_in_page, it in enumerate(batch):
            x, y = card_xy(i_in_page)
            draw_box(c, x, y, card_w, card_h, line_width=1)
            _draw_crop_marks(c, x=x, y=y, w=card_w, h=card_h, pol=pol)

            word = str(it.get("word", "")).strip()
            legacy = legacy_lookup.get(word, {}) if word else {}
            slug = _choose_icon_slug(
                subject,
                word,
                legacy_icon_slug=(legacy.get("icon_slug") if isinstance(legacy, dict) else None),
            )

            # Icon Zone
            icon_zone_h = card_h * float(pol["front_icon_ratio"])
            icon_size = min(icon_zone_h * 0.78, card_w * 0.55)
            cx = x + card_w / 2
            cy = y + card_h - icon_zone_h / 2

            draw_icon(c, slug, cx - icon_size / 2, cy - icon_size / 2, icon_size)

            # Wort groß darunter
            c.setFont("Helvetica-Bold", int(pol["front_word_font_size"]))
            c.setFillColor(colors.black)
            c.drawCentredString(cx, y + card_h * 0.40, word if word else "__________")

            # Mini label
            c.setFont("Helvetica", int(pol["front_label_font_size"]))
            c.setFillColor(colors.grey)
            c.drawCentredString(cx, y + 6 * mm, "Vorderseite")
            c.setFillColor(colors.black)

        c.showPage()

        # =========================
        # BACK PAGE (Satz + QR)
        # =========================
        if watermark:
            draw_brand_mark(c, page_w, page_h, mode="watermark", opacity=float(pol["watermark_opacity"]))

        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(outer_m, page_h - outer_m + 2 * mm, title)
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.grey)
        c.drawRightString(page_w - outer_m, page_h - outer_m + 2 * mm, meta)
        c.setFillColor(colors.black)

        for i_in_page, it in enumerate(batch):
            x, y = card_xy(i_in_page)
            draw_box(c, x, y, card_w, card_h, line_width=1)
            _draw_crop_marks(c, x=x, y=y, w=card_w, h=card_h, pol=pol)

            word = str(it.get("word", "")).strip()
            legacy = legacy_lookup.get(word, {}) if word else {}
            sentence = _pick_example_for_word(it, legacy)

            payload = f"{word}\n{sentence}".strip()
            qr_png = _make_qr_image_bytes(payload)

            # QR Zone (unten)
            qr_zone_h = card_h * float(pol["back_qr_ratio"])
            _text_zone_h = card_h - qr_zone_h

            # Text zone
            c.setFont("Helvetica-Bold", int(pol["back_title_font_size"]))
            c.setFillColor(colors.black)
            c.drawString(x + 6 * mm, y + card_h - 8 * mm, word if word else "__________")

            c.setFont("Helvetica", int(pol["back_text_font_size"]))
            c.setFillColor(colors.black)

            # Satz in 2-3 Zeilen umbrechen
            max_chars = 42
            s = sentence.strip()
            wrapped: List[str] = []
            while len(s) > max_chars and len(wrapped) < 3:
                cut = s.rfind(" ", 0, max_chars)
                if cut <= 0:
                    cut = max_chars
                wrapped.append(s[:cut].strip())
                s = s[cut:].strip()
            if s and len(wrapped) < 3:
                wrapped.append(s)

            ty = y + card_h - 16 * mm
            for ln in wrapped:
                c.drawString(x + 6 * mm, ty, ln)
                ty -= 5.2 * mm

            # QR Box
            pad = float(pol["qr_box_pad_mm"]) * mm
            qr_x = x + pad
            qr_y = y + pad
            qr_w = card_w - 2 * pad
            qr_h = qr_zone_h - 2 * pad

            # Optional: QR Rahmen
            if bool(pol["back_qr_border"]):
                c.saveState()
                c.setStrokeColor(colors.Color(0, 0, 0, alpha=0.35))
                c.setLineWidth(1)
                c.rect(qr_x, qr_y, qr_w, qr_h, stroke=1, fill=0)
                c.restoreState()

            # Fit QR square
            q_size = min(qr_w, qr_h)
            q_dx = qr_x + (qr_w - q_size) / 2
            q_dy = qr_y + (qr_h - q_size) / 2

            if qr_png:
                qr_reader = ImageReader(io.BytesIO(qr_png))
                c.drawImage(qr_reader, q_dx, q_dy, width=q_size, height=q_size, mask="auto")
            else:
                _draw_qr_fallback(c, x=q_dx, y=q_dy, w=q_size, h=q_size, payload=payload)

            # Mini label
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.grey)
            c.drawRightString(x + card_w - 6 * mm, y + 6 * mm, "Rückseite • QR offline")
            c.setFillColor(colors.black)

        c.showPage()
        start += per_page

    c.save()
    out.seek(0)
    return out.getvalue()
