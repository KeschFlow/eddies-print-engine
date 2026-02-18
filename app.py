# =========================================================
# app.py  (Eddies Print Engine — MODULAR / KDP)
# - Uses kern/pdf_engine.py page specs + brand mark
# - Uses kern/kdp_preflight.py ensure_min_pages()
# - KDP: min 24 pages, no page numbers, scrub metadata
# - Sketch: clean line-art for coloring
# - Optional image wash: if image_wash.py exists
# =========================================================
from __future__ import annotations

import io
import os
import hashlib
from typing import Any, Dict, List, Optional, Tuple, Callable

import streamlit as st
import cv2
import numpy as np
from PIL import Image

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

from kern.pdf_engine import get_page_spec, draw_brand_mark, draw_writing_area
from kern.kdp_preflight import ensure_min_pages

# --- Optional wash module (fixes odd decodes / strips EXIF / re-encode) ---
try:
    import image_wash as iw  # optional
except Exception:
    iw = None

# --- Quest DB ---
try:
    import quest_data as qd
except Exception as e:
    qd = None
    _QD_IMPORT_ERROR = str(e)
else:
    _QD_IMPORT_ERROR = ""


# =========================================================
# Config
# =========================================================
APP_TITLE = "Eddies"
APP_ICON = "🐶"

KDP_MIN_PAGES = 24
DPI = 300

INK_BLACK = colors.Color(0, 0, 0)
INK_GRAY = colors.Color(0.30, 0.30, 0.30)

# PageFn signature: (canvas, ctx) -> None
PageFn = Callable[[canvas.Canvas, Dict[str, Any]], None]


# =========================================================
# Utilities
# =========================================================
def _stable_seed(s: str) -> int:
    h = hashlib.sha256((s or "").encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big", signed=False)


def _scrub_pdf_metadata(c: canvas.Canvas) -> None:
    """No author/creator/title defaults in PDF info."""
    try:
        c.setAuthor("")
        c.setTitle("")
        c.setSubject("")
        c.setCreator("")
        c.setKeywords("")
    except Exception:
        pass
    try:
        if hasattr(c, "_doc") and hasattr(c._doc, "info") and c._doc.info:
            c._doc.info.producer = ""
            c._doc.info.author = ""
            c._doc.info.title = ""
            c._doc.info.subject = ""
            c._doc.info.creator = ""
            c._doc.info.keywords = ""
    except Exception:
        pass


def _bytes_maybe_wash(img_bytes: bytes) -> bytes:
    """If image_wash.py exists, run it; otherwise passthrough."""
    if iw is None:
        return img_bytes
    # Try common function names (since we don't know exact API)
    for fn_name in ("wash_bytes", "wash_image_bytes", "sanitize_bytes", "wash"):
        fn = getattr(iw, fn_name, None)
        if callable(fn):
            try:
                out = fn(img_bytes)
                if isinstance(out, (bytes, bytearray)) and len(out) > 0:
                    return bytes(out)
            except Exception:
                pass
    return img_bytes


# =========================================================
# Sketch Engine (clean line-art, max white)
# =========================================================
def _cv_line_art(img_bytes: bytes) -> np.ndarray:
    arr = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if arr is None:
        raise RuntimeError("Bild-Dekodierung fehlgeschlagen (OpenCV).")

    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, d=9, sigmaColor=80, sigmaSpace=80)

    edges = cv2.Canny(gray, threshold1=40, threshold2=120)
    edges = cv2.dilate(edges, np.ones((2, 2), np.uint8), iterations=1)

    line_art = 255 - edges
    line_art = cv2.medianBlur(line_art, 3)
    return line_art.astype(np.uint8)


def _pil_page_image_from_upload(
    upload_bytes: bytes,
    page_w: float,
    page_h: float,
) -> Image.Image:
    """
    Build a full-page grayscale image at 300dpi pixel size.
    Center-crop square -> resize to page pixels.
    """
    b = _bytes_maybe_wash(upload_bytes)
    sk = _cv_line_art(b)
    pil = Image.fromarray(sk).convert("L")

    sw, sh = pil.size
    s = min(sw, sh)
    pil = pil.crop(((sw - s) // 2, (sh - s) // 2, (sw + s) // 2, (sh + s) // 2))

    px_w = int(page_w * DPI / inch)
    px_h = int(page_h * DPI / inch)
    pil = pil.resize((px_w, px_h), Image.LANCZOS)
    return pil


# =========================================================
# Page Builders (PageFn)
# =========================================================
def _page_intro(name: str) -> PageFn:
    def _fn(c: canvas.Canvas, ctx: Dict[str, Any]) -> None:
        w, h = ctx["page_w"], ctx["page_h"]
        margin = ctx["margin"]

        c.setFillColor(colors.white)
        c.rect(0, 0, w, h, fill=1, stroke=0)

        # Brand watermark (subtle)
        draw_brand_mark(c, w, h, mode="watermark", scale=1.0, opacity=0.06)

        c.setFillColor(INK_BLACK)
        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(w / 2, h - margin - 0.9 * inch, "EDDIES QUESTBUCH")

        c.setFont("Helvetica", 18)
        c.setFillColor(INK_GRAY)
        c.drawCentredString(w / 2, h - margin - 1.35 * inch, f"für {name}")

        # Simple instruction block
        c.setFillColor(INK_BLACK)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, h - margin - 2.1 * inch, "So läuft’s:")
        c.setFont("Helvetica", 12)
        c.drawString(margin, h - margin - 2.45 * inch, "• Jede Seite = 1 Mission")
        c.drawString(margin, h - margin - 2.75 * inch, "• Ausmalen + Bewegung + Denken")
        c.drawString(margin, h - margin - 3.05 * inch, "• XP sammeln, Haken setzen")

        # Big writing area
        draw_writing_area(
            c,
            margin,
            margin,
            w - 2 * margin,
            2.2 * inch,
            line_spacing=14,
            border=True,
            lines=True,
        )

    return _fn


def _page_outro(total_xp: int) -> PageFn:
    def _fn(c: canvas.Canvas, ctx: Dict[str, Any]) -> None:
        w, h = ctx["page_w"], ctx["page_h"]
        margin = ctx["margin"]

        c.setFillColor(colors.white)
        c.rect(0, 0, w, h, fill=1, stroke=0)

        draw_brand_mark(c, w, h, mode="watermark", scale=1.0, opacity=0.06)

        c.setFillColor(INK_BLACK)
        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(w / 2, h - margin - 1.0 * inch, "QUEST ABGESCHLOSSEN!")

        c.setFont("Helvetica", 16)
        c.setFillColor(INK_GRAY)
        c.drawCentredString(w / 2, h - margin - 1.55 * inch, f"Dein Score: {int(total_xp)} XP")

        c.setFillColor(INK_BLACK)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, h - margin - 2.3 * inch, "Was war heute stark?")
        draw_writing_area(
            c,
            margin,
            margin,
            w - 2 * margin,
            3.0 * inch,
            line_spacing=14,
            border=True,
            lines=True,
        )

    return _fn


def _page_reflection(page_no: int) -> PageFn:
    """
    Filler page for ensure_min_pages().
    No numbers printed (page_no only influences internal variation if you want later).
    """
    def _fn(c: canvas.Canvas, ctx: Dict[str, Any]) -> None:
        w, h = ctx["page_w"], ctx["page_h"]
        margin = ctx["margin"]

        c.setFillColor(colors.white)
        c.rect(0, 0, w, h, fill=1, stroke=0)

        draw_brand_mark(c, w, h, mode="watermark", scale=1.0, opacity=0.05)

        c.setFillColor(INK_BLACK)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margin, h - margin - 0.75 * inch, "REFLEXION")

        c.setFont("Helvetica", 12)
        c.setFillColor(INK_GRAY)
        c.drawString(margin, h - margin - 1.1 * inch, "• Was lief gut?")
        c.drawString(margin, h - margin - 1.35 * inch, "• Was war schwer?")
        c.drawString(margin, h - margin - 1.6 * inch, "• Was mache ich morgen besser?")

        draw_writing_area(
            c,
            margin,
            margin,
            w - 2 * margin,
            h - 2 * margin - 2.0 * inch,
            line_spacing=14,
            border=True,
            lines=True,
        )

    return _fn


def _page_mission(
    *,
    upload_bytes: bytes,
    hour: int,
    mission: Any,
    idx: int,
    total: int,
    cum_xp: int,
    total_xp: int,
) -> PageFn:
    def _fn(c: canvas.Canvas, ctx: Dict[str, Any]) -> None:
        w, h = ctx["page_w"], ctx["page_h"]
        margin = ctx["margin"]

        # Background: full-page line-art image
        pil = _pil_page_image_from_upload(upload_bytes, w, h)
        ib = io.BytesIO()
        pil.save(ib, "PNG")
        ib.seek(0)
        c.drawImage(ImageReader(ib), 0, 0, w, h)

        # Header bar (zone color)
        zone = qd.get_zone_for_hour(hour)
        z_r, z_g, z_b = qd.get_hour_color(hour)
        fill = colors.Color(z_r, z_g, z_b)

        header_h = 0.72 * inch
        c.setFillColor(fill)
        c.rect(margin, h - margin - header_h, w - 2 * margin, header_h, fill=1, stroke=0)

        # Header text
        c.setFillColor(colors.white if (0.21*z_r + 0.71*z_g + 0.07*z_b) < 0.45 else INK_BLACK)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin + 0.18 * inch, h - margin - 0.48 * inch, f"{qd.fmt_hour(hour)}  {zone.icon}  {zone.name}")

        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(margin + (w - 2 * margin) - 0.18 * inch, h - margin - 0.30 * inch, f"MISSION {idx+1:02d}/{total:02d}")

        # Mission card bottom
        card_h = 2.1 * inch
        c.setFillColor(colors.white)
        c.setStrokeColor(INK_BLACK)
        c.setLineWidth(1)
        c.rect(margin, margin, w - 2 * margin, card_h, fill=1, stroke=1)

        c.setFillColor(INK_BLACK)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin + 0.15 * inch, margin + card_h - 0.40 * inch, f"MISSION: {mission.title}")
        c.drawRightString(margin + (w - 2 * margin) - 0.15 * inch, margin + card_h - 0.40 * inch, f"+{int(mission.xp)} XP")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin + 0.15 * inch, margin + 1.25 * inch, "BEWEGUNG:")
        c.drawString(margin + 0.15 * inch, margin + 0.75 * inch, "DENKEN:")
        c.drawString(margin + 0.15 * inch, margin + 0.25 * inch, "PROOF:")

        c.setFont("Helvetica", 9)
        c.drawString(margin + 1.2 * inch, margin + 1.25 * inch, (mission.movement or "")[:92])
        c.drawString(margin + 1.2 * inch, margin + 0.75 * inch, (mission.thinking or "")[:92])
        c.drawString(margin + 1.2 * inch, margin + 0.25 * inch, (mission.proof or "")[:92])

        # XP bar (simple)
        bar_w = 1.6 * inch
        bar_h = 0.12 * inch
        bx = margin
        by = margin + card_h + 0.18 * inch
        progress = float(cum_xp) / float(max(1, total_xp))

        c.setStrokeColor(INK_BLACK)
        c.setLineWidth(0.8)
        c.rect(bx, by, bar_w, bar_h, stroke=1, fill=0)
        if progress > 0:
            c.setFillColor(INK_BLACK)
            c.rect(bx, by, bar_w * min(1.0, progress), bar_h, stroke=0, fill=1)

        # Brand watermark (very subtle, to keep coloring clean)
        draw_brand_mark(c, w, h, mode="watermark", scale=0.85, opacity=0.03)

    return _fn


# =========================================================
# PDF Export (modular pages + preflight)
# =========================================================
def build_interior_pdf(
    *,
    name: str,
    uploads: List[Any],
    mode: str,
    start_hour: int,
    difficulty: int,
    min_pages: int = KDP_MIN_PAGES,
) -> bytes:
    if qd is None:
        raise RuntimeError(f"quest_data.py nicht verfügbar: {_QD_IMPORT_ERROR}")

    spec = get_page_spec(mode)
    page_w, page_h = spec["pagesize"]
    margin = spec["margin"]

    # Build base pages: intro + missions + outro
    files = list(uploads or [])
    if not files:
        raise RuntimeError("Keine Bilder hochgeladen.")

    # We'll generate up to (min_pages - 2) mission pages, then preflight fills if needed.
    seed_base = _stable_seed(name)

    # build a reasonably sized mission block from uploads
    # Start with photo pages = max(1, len(files)) but bounded so we don’t explode
    base_mission_pages = max(1, min(22, len(files)))  # intro+outro => at least 3 total before fill
    mission_total = base_mission_pages

    pages: List[PageFn] = []
    pages.append(_page_intro(name))

    # repeat uploads if needed
    repeated = (files * (mission_total // len(files) + 1))[:mission_total]

    missions: List[Any] = []
    for i in range(mission_total):
        h = (int(start_hour) + i) % 24
        m = qd.pick_mission_for_time(h, int(difficulty), int(seed_base ^ i), audience="kid")
        missions.append(m)

    total_xp = sum(int(getattr(m, "xp", 0) or 0) for m in missions) or 1
    cum = 0

    for i, up in enumerate(repeated):
        h = (int(start_hour) + i) % 24
        m = missions[i]
        cum += int(getattr(m, "xp", 0) or 0)
        pages.append(
            _page_mission(
                upload_bytes=up.getvalue(),
                hour=h,
                mission=m,
                idx=i,
                total=mission_total,
                cum_xp=cum,
                total_xp=total_xp,
            )
        )

    pages.append(_page_outro(total_xp=cum))

    # Preflight: ensure min pages (KDP 24) with reflection pages
    pages = ensure_min_pages(
        pages,
        min_pages=int(min_pages),
        make_reflection_page=lambda n: _page_reflection(n),
    )

    # Render
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))
    _scrub_pdf_metadata(c)

    ctx = {"page_w": page_w, "page_h": page_h, "margin": margin, "bleed": spec.get("bleed", 0.0), "mode": mode}

    for fn in pages:
        fn(c, ctx)
        c.showPage()

    c.save()
    return buf.getvalue()


# =========================================================
# Streamlit UI
# =========================================================
st.set_page_config(page_title=APP_TITLE, layout="centered", page_icon=APP_ICON)

st.markdown(
    "<style>div[data-testid='stFileUploader'] small { display: none !important; }</style>",
    unsafe_allow_html=True,
)

st.markdown(f"<h1 style='text-align:center;'>{APP_TITLE} Print Engine</h1>", unsafe_allow_html=True)

with st.container(border=True):
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Name", value="Eddie")
        age = st.number_input("Alter", 3, 12, 5)
    with c2:
        mode = st.selectbox("Export-Modus", ["KDP Buch", "A4 Arbeitsblatt"], index=0)
        start_hour = st.number_input("Start-Stunde", 0, 23, 6)

    uploads = st.file_uploader("Fotos hochladen", accept_multiple_files=True, type=["jpg", "jpeg", "png"])

if uploads:
    st.markdown(f"**📷 Bilder: {len(uploads)}**")
    idx = st.slider("Vorschau", 1, len(uploads), 1) if len(uploads) > 1 else 1
    st.image(Image.open(io.BytesIO(uploads[idx - 1].getvalue())), use_container_width=True)

if st.button("🚀 PDF generieren", disabled=not (uploads and name)):
    if qd is None:
        st.error(f"quest_data.py konnte nicht geladen werden: {_QD_IMPORT_ERROR}")
    else:
        with st.spinner("Erstelle druckfertiges PDF..."):
            # map age -> difficulty (1..5 supported by DB)
            diff = 1 if age <= 4 else 2 if age <= 6 else 3 if age <= 9 else 4

            pdf_bytes = build_interior_pdf(
                name=name,
                uploads=uploads,
                mode=mode,
                start_hour=int(start_hour),
                difficulty=int(diff),
                min_pages=KDP_MIN_PAGES if mode == "KDP Buch" else 1,
            )
            st.session_state.pdf = pdf_bytes
            st.session_state.pdf_name = name
            st.success("PDF bereit!")

if "pdf" in st.session_state:
    st.download_button("📘 Download PDF", st.session_state.pdf, file_name=f"Eddies_{st.session_state.pdf_name}.pdf")

st.markdown(
    "<div style='text-align:center; color:grey; margin-top:2rem;'>Eddies Welt | Print Engine</div>",
    unsafe_allow_html=True,
)