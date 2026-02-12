# app_trainer.py
from __future__ import annotations

import io
from typing import List, Tuple

import streamlit as st
from reportlab.pdfgen import canvas  # <-- FIX: fehlte vorher

from kern.pdf_engine import get_page_spec, draw_box, embed_image


def parse_vocab_lines(raw: str) -> List[Tuple[str, str]]:
    """
    Pro Zeile:
      deutsch;übersetzung
    oder nur:
      deutsch
    """
    items: List[Tuple[str, str]] = []
    for line in (raw or "").splitlines():
        s = line.strip()
        if not s:
            continue

        parts = [p.strip() for p in s.split(";")]
        if len(parts) == 1:
            items.append((parts[0], ""))
        else:
            items.append((parts[0], ";".join(parts[1:]).strip()))
    return items


def build_trainer_pdf(
    *,
    vocab: List[Tuple[str, str]],
    uploads: List,
    kdp_mode: bool,
) -> bytes:
    spec = get_page_spec(kdp_mode=kdp_mode)
    page_w, page_h, safe = spec.page_w, spec.page_h, spec.safe

    img_buffers = [io.BytesIO(up.getvalue()) for up in (uploads or [])]

    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(page_w, page_h))

    header_h = 60
    word_box_h = 120
    img_box_h = 220
    notes_h = 120
    gap = 16

    usable_w = page_w - 2 * safe
    img_idx = 0

    for i, (word, translation) in enumerate(vocab, 1):
        top = page_h - safe

        # Header
        c.setFont("Helvetica-Bold", 20)
        c.drawString(safe, top - 30, f"Vokabel {i} / {len(vocab)}")

        # Wort
        y_word = top - header_h
        draw_box(c, safe, y_word - word_box_h, usable_w, word_box_h, title="WORT")
        c.setFont("Helvetica-Bold", 32)
        c.drawCentredString(page_w / 2, y_word - 70, (word or "")[:35])

        if translation:
            c.setFont("Helvetica", 16)
            c.drawCentredString(page_w / 2, y_word - 105, translation[:60])

        # Bild
        y_img = y_word - word_box_h - gap
        if img_buffers:
            draw_box(c, safe, y_img - img_box_h, usable_w, img_box_h, title="BILD")
            buf = img_buffers[img_idx % len(img_buffers)]
            buf.seek(0)
            embed_image(
                c,
                img_data=buf,
                x=safe,
                y=y_img - img_box_h,
                max_w=usable_w,
                max_h=img_box_h,
                preserve_aspect=True,
                scale_to=0.75,
                debug_on_error=False,
            )
            img_idx += 1
        else:
            draw_box(c, safe, y_img - img_box_h, usable_w, img_box_h, title="BILD (optional)")

        # Notizen
        y_notes = y_img - img_box_h - gap
        draw_box(c, safe, y_notes - notes_h, usable_w, notes_h, title="NOTIZEN")
        c.setFont("Helvetica", 11)
        c.drawString(safe + 12, y_notes - 35, "Beispielsatz oder eigene Notizen:")

        c.showPage()

    c.save()
    out.seek(0)
    return out.getvalue()


# ---------------- UI ----------------
st.set_page_config(page_title="Eddie Trainer V2", layout="centered")
st.title("🗣️ Eddie Trainer V2 – Fachsprache mit Bildern")

with st.sidebar:
    kdp = st.toggle("KDP-Modus (8.5×8.5 + Bleed)", value=True)

raw_text = st.text_area(
    "Vokabeln (Format: deutsch;übersetzung oder nur deutsch)",
    value="die Nadel;needle\nStoff;fabric\nSchere;scissors",
    height=200,
)

uploads = st.file_uploader(
    "Bilder (werden zyklisch verteilt)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

vocab = parse_vocab_lines(raw_text)

if st.button("PDF erstellen", type="primary", disabled=not vocab):
    try:
        pdf_data = build_trainer_pdf(vocab=vocab, uploads=uploads or [], kdp_mode=kdp)
        st.success("PDF erstellt")
        st.download_button(
            "PDF herunterladen",
            pdf_data,
            file_name="eddie_trainer_v2.pdf",
            mime="application/pdf",
        )
    except Exception as e:
        st.error(f"Fehler beim Erstellen: {e}")
