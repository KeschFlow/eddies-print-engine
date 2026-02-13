# kern/exports/trainer_kdp.py
from __future__ import annotations

import io
from typing import Dict, Any, List, Optional

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

from kern.pdf_engine import (
    get_page_spec,
    draw_box,
    draw_brand_mark,
    draw_writing_area,
)

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

    items = data.get("items")
    if isinstance(items, list) and items:
        out2: List[Dict[str, str]] = []
        for it in items:
            if isinstance(it, dict):
                w = str(it.get("term", "")).strip()
                if w:
                    out2.append({"word": w, "translation": ""})
        return out2

    return []

def _coerce_images(data: Dict[str, Any]) -> List[bytes]:
    assets = data.get("assets")
    if not isinstance(assets, dict):
        return []
    imgs = assets.get("images")
    if not isinstance(imgs, list):
        return []
    out: List[bytes] = []
    for b in imgs:
        if isinstance(b, (bytes, bytearray)) and len(b) > 0:
            out.append(bytes(b))
    return out

def _draw_image_safe(c: canvas.Canvas, img_bytes: bytes, x: float, y: float, w: float, h: float) -> None:
    try:
        ir = ImageReader(io.BytesIO(img_bytes))
        c.drawImage(ir, x, y, width=w, height=h, preserveAspectRatio=True, anchor="c", mask="auto")
    except Exception:
        # stiller Fallback
        c.saveState()
        c.setStrokeColor(colors.Color(0, 0, 0, alpha=0.2))
        c.rect(x, y, w, h, stroke=1, fill=0)
        c.restoreState()

def export_trainer_kdp(
    data: Dict[str, Any],
    *,
    title: str = "Eddie Trainer V2",
    subtitle: Optional[str] = None,
    watermark: bool = True,
    policy: Optional[Dict[str, Any]] = None,
    min_pages: int = 24,
) -> bytes:
    """
    KDP Buch (Square):
    - simple Seiten: oben Wort + optional Bild, unten Schreiblinien
    - Seiten werden auf min_pages aufgefüllt (KDP Preflight)
    """
    if not isinstance(data, dict):
        raise ValueError("export_trainer_kdp: data must be a dict")

    spec = get_page_spec("KDP Buch")
    page_w, page_h = spec["pagesize"]
    margin = float(spec["margin"])

    subject = str(data.get("subject") or "").strip()
    vocab = _coerce_vocab(data)
    images = _coerce_images(data)

    if not vocab:
        vocab = [{"word": "", "translation": ""}]

    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(page_w, page_h))

    img_i = 0

    def header() -> None:
        if watermark:
            draw_brand_mark(c, page_w, page_h, mode="watermark", opacity=0.04)

        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin, page_h - margin + 2 * mm, title)

        c.setFont("Helvetica", 9)
        meta = subtitle or (f"Fach: {subject}" if subject else "Trainer")
        c.setFillColor(colors.grey)
        c.drawRightString(page_w - margin, page_h - margin + 2 * mm, meta)
        c.setFillColor(colors.black)

    # Pro Seite: 1 Wort (sauber für KDP)
    pages = 0
    for it in vocab:
        header()

        word = str(it.get("word", "")).strip()
        trans = str(it.get("translation", "")).strip()

        # Top Box
        top_h = (page_h - 2 * margin) * 0.42
        box_x = margin
        box_y = page_h - margin - top_h
        box_w = page_w - 2 * margin
        draw_box(c, box_x, box_y, box_w, top_h, line_width=1)

        # Wort/Übersetzung
        c.setFont("Helvetica-Bold", 18)
        c.drawString(box_x + 8 * mm, box_y + top_h - 10 * mm, word if word else "__________")

        if trans:
            c.setFont("Helvetica", 12)
            c.setFillColor(colors.Color(0, 0, 0, alpha=0.75))
            c.drawString(box_x + 8 * mm, box_y + top_h - 18 * mm, trans)
            c.setFillColor(colors.black)

        # optional Bild rechts
        if images:
            img = images[img_i % len(images)]
            img_i += 1
            ix = box_x + box_w * 0.58
            iy = box_y + 6 * mm
            iw = box_w * 0.40 - 8 * mm
            ih = top_h - 12 * mm
            _draw_image_safe(c, img, ix, iy, iw, ih)

        # Schreibbereich unten
        low_y = margin
        low_h = box_y - margin - 6 * mm
        draw_writing_area(
            c,
            x=margin,
            y=low_y,
            w=page_w - 2 * margin,
            h=low_h,
            lines=10,
            line_alpha=0.18,
        )

        c.showPage()
        pages += 1

    # Auffüllen auf min_pages (KDP)
    while pages < int(min_pages):
        header()
        draw_writing_area(
            c,
            x=margin,
            y=margin,
            w=page_w - 2 * margin,
            h=page_h - 2 * margin - 6 * mm,
            lines=12,
            line_alpha=0.14,
        )
        c.showPage()
        pages += 1

    c.save()
    out.seek(0)
    return out.getvalue()
