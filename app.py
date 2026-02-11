import streamlit as st
import cv2
import os
import io
import random
import tempfile
import re
import zipfile
import numpy as np
from datetime import datetime

from PIL import Image, ImageDraw

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

# Stripe is optional: app works without it in PAYWALL_MODE="soft"
try:
    import stripe  # type: ignore
except Exception:
    stripe = None

# =========================================================
# BUSINESS & BRAND CONFIG
# =========================================================

APP_TITLE = "Eddie Publishing System"
APP_ICON = "🐶"

# Eddie rules
EDDIE_TONGUE_COLOR_HEX = "#7c3aed"  # purple tongue

# KDP interior config
DPI = 300
TRIM_IN = 8.5
TRIM = TRIM_IN * inch
BLEED = 0.125 * inch
SAFE_INTERIOR = 0.375 * inch

DEFAULT_PAGES = 24
KDP_MIN_PAGES = 24  # for our product (can raise later)

# KDP cover config
COVER_SAFE = 0.25 * inch
SPINE_TEXT_MIN_PAGES = 79  # avoid KDP rejections

PAPER_FACTORS = {
    "Schwarzweiß – Weiß": 0.002252,
    "Schwarzweiß – Creme": 0.0025,
    "Farbe – Weiß": 0.002347,
}

HUB_URL = "https://eddieswelt.de"

# Paywall:
# - "soft": ZIP is always downloadable, Stripe is optional support button
# - "hard": ZIP is downloadable only after Stripe session is verified paid
PAYWALL_MODE = "soft"

# Derived sizes
INTERIOR_W = TRIM + 2 * BLEED
INTERIOR_H = TRIM + 2 * BLEED
INTERIOR_PAGE_SIZE = (INTERIOR_W, INTERIOR_H)

# =========================================================
# STREAMLIT CONFIG + STYLING
# =========================================================
st.set_page_config(page_title=APP_TITLE, layout="centered", page_icon=APP_ICON)

st.markdown(
    """
<style>
:root{
  --ink:#0b0b0f; --muted:#6b7280; --panel:#fafafa; --line:#e5e7eb; --accent:#7c3aed;
}
.main-title{font-size:2.5rem; font-weight:900; text-align:center; letter-spacing:-0.03em; color:var(--ink); margin-bottom:0;}
.subtitle{text-align:center; font-size:1.05rem; color:var(--muted); margin-bottom:1.4rem;}
.card{background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:22px; margin-bottom:18px;}
.hr{height:1px; background:var(--line); margin:22px 0;}
.footer{text-align:center; font-size:.85rem; color:var(--muted); margin-top:34px;}
.kpi-container{display:flex; justify-content:center; gap:10px; margin-bottom:16px; flex-wrap:wrap;}
.kpi{padding:5px 12px; border-radius:999px; border:1px solid var(--line); font-size:.78rem; font-weight:700; color:var(--muted); background:#fff;}
.stButton>button {width: 100%; border-radius: 12px; font-weight: 800; padding: 0.65rem; border: 2px solid #000;}
small{color:var(--muted);}
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# HELPERS
# =========================================================
def _sanitize_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "file"


def _draw_eddie_brand_pdf(c: canvas.Canvas, cx: float, cy: float, r: float):
    """Minimal Eddie: B/W + purple tongue."""
    c.saveState()
    c.setLineWidth(max(2, r * 0.06))
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.white)
    c.circle(cx, cy, r, stroke=1, fill=1)

    # eyes
    eye_r = r * 0.10
    c.setFillColor(colors.black)
    c.circle(cx - r * 0.28, cy + r * 0.15, eye_r, stroke=0, fill=1)
    c.circle(cx + r * 0.28, cy + r * 0.15, eye_r, stroke=0, fill=1)

    # mouth arc
    c.setLineWidth(max(2, r * 0.05))
    c.arc(cx - r * 0.35, cy - r * 0.10, cx + r * 0.35, cy + r * 0.20, 200, 140)

    # tongue
    c.setFillColor(colors.HexColor(EDDIE_TONGUE_COLOR_HEX))
    c.roundRect(cx - r * 0.10, cy - r * 0.35, r * 0.20, r * 0.22, r * 0.08, stroke=0, fill=1)
    c.restoreState()


def _cv_sketch_from_bytes(img_bytes: bytes) -> np.ndarray:
    """Bytes -> sketch grayscale array."""
    arr = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if arr is None:
        raise RuntimeError("Bild konnte nicht dekodiert werden.")
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    inverted = 255 - gray
    blurred = cv2.GaussianBlur(inverted, (21, 21), 0)
    sketch = cv2.divide(gray, 255 - blurred, scale=256.0)
    sketch = cv2.normalize(sketch, None, 0, 255, cv2.NORM_MINMAX)
    return sketch


def _center_crop_resize_square(pil_img: Image.Image, side_px: int) -> Image.Image:
    """Center-crop to square and resize."""
    w, h = pil_img.size
    s = min(w, h)
    left = (w - s) // 2
    top = (h - s) // 2
    pil_img = pil_img.crop((left, top, left + s, top + s))
    pil_img = pil_img.resize((side_px, side_px), Image.LANCZOS)
    return pil_img


def preflight_uploads_for_300dpi(uploads, target_inch: float):
    """Check if images are likely sufficient for 300dpi full-bleed."""
    target_px = int(round(target_inch * DPI))
    ok = 0
    warn = 0
    details = []
    for up in uploads:
        try:
            up.seek(0)
            img = Image.open(up)
            w, h = img.size
            if min(w, h) >= target_px:
                ok += 1
                details.append((up.name, w, h, "OK"))
            else:
                warn += 1
                details.append((up.name, w, h, "LOW"))
        except Exception:
            warn += 1
            details.append((getattr(up, "name", "unknown"), 0, 0, "READ_FAIL"))
    return ok, warn, details


def build_front_cover_preview_png(child_name: str, size_px: int = 900) -> bytes:
    """Fast front-cover preview for UI confidence."""
    img = Image.new("RGB", (size_px, size_px), "white")
    d = ImageDraw.Draw(img)

    cx, cy = size_px // 2, int(size_px * 0.45)
    r = int(size_px * 0.20)

    # face
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline="black", width=max(2, r // 10), fill="white")

    # eyes
    eye_r = max(3, r // 10)
    d.ellipse((cx - int(r * 0.28) - eye_r, cy - int(r * 0.15) - eye_r,
               cx - int(r * 0.28) + eye_r, cy - int(r * 0.15) + eye_r), fill="black")
    d.ellipse((cx + int(r * 0.28) - eye_r, cy - int(r * 0.15) - eye_r,
               cx + int(r * 0.28) + eye_r, cy - int(r * 0.15) + eye_r), fill="black")

    # tongue (purple)
    tongue_w = int(r * 0.22)
    tongue_h = int(r * 0.22)
    tx0 = cx - tongue_w // 2
    ty0 = cy + int(r * 0.35) - tongue_h
    d.rounded_rectangle((tx0, ty0, tx0 + tongue_w, ty0 + tongue_h),
                        radius=max(2, tongue_w // 4),
                        fill=EDDIE_TONGUE_COLOR_HEX)

    # title
    d.text((size_px * 0.5, size_px * 0.84), "EDDIE", fill="black", anchor="mm")
    d.text((size_px * 0.5, size_px * 0.90), f"& {child_name}", fill=(90, 90, 90), anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _calc_spine_inch(page_count: int, paper_key: str) -> float:
    factor = PAPER_FACTORS.get(paper_key, PAPER_FACTORS["Schwarzweiß – Weiß"])
    return float(page_count) * float(factor)


def build_listing_text(child_name: str) -> str:
    title = f"Eddie & {child_name}"
    subtitle = (
        "Mein ganz persönliches Malbuch aus echten Momenten – "
        "Ein kreatives Abenteuer für Kinder ab 4 Jahren (Personalisiertes Geschenk)"
    )
    keywords = [
        "Personalisiertes Malbuch Kinder",
        "Malbuch mit eigenen Fotos",
        "Geschenk Schulanfang Junge Mädchen",
        "Kreativbuch personalisiert",
        "Fotogeschenk Kinder kreativ",
        "Eddie Malbuch Terrier",
        "Malen nach Fotos Abenteuer",
    ]
    html = f"""<h3>Lasse deine schönsten Momente lebendig werden!</h3>
<p>Was passiert, wenn deine eigenen Fotos zu magischen Ausmalbildern werden?
<b>Eddie</b> begleitet dich auf einer ganz besonderen Reise – und <b>{child_name}</b> steht im Mittelpunkt dieses Abenteuers.</p>

<p>In diesem Buch ist nichts gewöhnlich:</p>
<ul>
  <li><b>Vollständig personalisiert:</b> Jede Seite basiert auf deinen hochgeladenen Bildern.</li>
  <li><b>Eddie ist immer dabei:</b> Der treue schwarz-weiße Terrier führt dich durch das Buch.</li>
  <li><b>Viel Platz für Fantasie:</b> Große, offene Flächen laden dazu ein, die Welt um Eddie herum bunt zu gestalten.</li>
  <li><b>Hochwertiges Design:</b> Optimiert für den Druck und perfekt für kleine Künstlerhände.</li>
</ul>
<p><i>Hinweis: Eddie bleibt in seinem klassischen Look (schwarz-weiß mit purpurfarbener Zunge) – du gestaltest seine gesamte Umgebung!</i></p>
"""
    aplus = (
        "A+ Content Blueprint (3 Banner):\n"
        "1) Header: Foto vs. Ausmalseite (Transformation / Wow)\n"
        "2) Eddie Brand: Eddie Close-up (B/W + purpur Zunge)\n"
        "3) Qualität: 300 DPI Linien-Detail (Profi-Druck)\n"
    )

    out = [
        "READY-TO-PUBLISH LISTING BUNDLE (KDP)",
        f"TITEL: {title}",
        f"UNTERTITEL: {subtitle}",
        "",
        "KEYWORDS (7 Felder):",
        "\n".join([f"{i+1}. {k}" for i, k in enumerate(keywords)]),
        "",
        "BESCHREIBUNG (HTML):",
        html,
        "",
        aplus,
    ]
    return "\n".join(out)


# =========================================================
# BUILDERS (Interior + CoverWrap)
# =========================================================
def build_interior_pdf(child_name: str, uploads, pages: int, eddie_mark_inside: bool) -> bytes:
    """Build interior PDF bytes."""
    side_px = int(round((INTERIOR_W / inch) * DPI))

    # Deterministic seed (series-friendly)
    seed_parts = [f"{_sanitize_filename(u.name)}:{getattr(u, 'size', 0)}" for u in uploads]
    random.seed((child_name.strip() + "|" + "|".join(seed_parts)).encode("utf-8", errors="ignore"))

    files = list(uploads)
    if not files:
        raise RuntimeError("Bitte mindestens 1 Foto hochladen.")

    # Ensure enough pages (repeat deterministically)
    final = list(files)
    while len(final) < pages:
        tmp = list(files)
        random.shuffle(tmp)
        final.extend(tmp)
    final = final[:pages]

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=INTERIOR_PAGE_SIZE)

    for i, up in enumerate(final):
        try:
            up.seek(0)
            img_bytes = up.read()
            sketch_arr = _cv_sketch_from_bytes(img_bytes)
            pil = Image.fromarray(sketch_arr).convert("L")
            pil = _center_crop_resize_square(pil, side_px)
            c.drawImage(ImageReader(pil), 0, 0, width=INTERIOR_W, height=INTERIOR_H)
        except Exception:
            c.setFillColor(colors.white)
            c.rect(0, 0, INTERIOR_W, INTERIOR_H, fill=1, stroke=0)

        if eddie_mark_inside:
            m = BLEED + SAFE_INTERIOR
            _draw_eddie_brand_pdf(c, INTERIOR_W - m, m, 0.20 * inch)

        c.showPage()

    c.save()
    buf.seek(0)
    return buf.getvalue()


def build_cover_wrap_pdf(child_name: str, page_count: int, paper_key: str) -> bytes:
    """Build Full Wrap Cover PDF (Back + Spine + Front)."""
    spine_in = _calc_spine_inch(page_count, paper_key)
    spine_w = spine_in * inch

    cover_w = (2 * TRIM) + spine_w + (2 * BLEED)
    cover_h = TRIM + (2 * BLEED)

    # Coordinates: [BLEED][BACK][SPINE][FRONT][BLEED]
    back_x0 = BLEED
    spine_x0 = BLEED + TRIM
    front_x0 = BLEED + TRIM + spine_w

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(cover_w, cover_h))

    # Background full bleed
    c.setFillColor(colors.white)
    c.rect(0, 0, cover_w, cover_h, fill=1, stroke=0)

    # BACK: minimal imprint + barcode keepout
    safe_x = back_x0 + COVER_SAFE
    safe_y = BLEED + COVER_SAFE
    safe_h = TRIM - 2 * COVER_SAFE

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 12)
    c.drawString(safe_x, safe_y + safe_h - 14, "Eddie’s Welt")

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.grey)
    c.drawString(safe_x, safe_y + safe_h - 30, "Erstellt mit dem Eddie Publishing System")

    # Barcode keep-out bottom-right of back trim
    box_w, box_h = 2.0 * inch, 1.2 * inch
    box_x = back_x0 + TRIM - COVER_SAFE - box_w
    box_y = BLEED + COVER_SAFE
    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(1)
    c.rect(box_x, box_y, box_w, box_h, fill=0, stroke=1)
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.lightgrey)
    c.drawCentredString(box_x + box_w / 2, box_y + box_h / 2 - 3, "Barcode area (KDP)")

    # SPINE: fill exact spine
    c.setFillColor(colors.black)
    c.rect(spine_x0, BLEED, spine_w, TRIM, fill=1, stroke=0)

    # Spine content rules
    if page_count >= SPINE_TEXT_MIN_PAGES and spine_w >= 0.08 * inch:
        c.saveState()
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.translate(spine_x0 + spine_w / 2, BLEED + TRIM / 2)
        c.rotate(90)
        c.drawCentredString(0, -4, f"Eddie & {child_name}".upper())
        c.restoreState()
    else:
        _draw_eddie_brand_pdf(c, spine_x0 + spine_w / 2, BLEED + TRIM / 2, r=min(0.18 * inch, max(spine_w, 0.06 * inch) * 0.35))

    # FRONT: hero Eddie + title
    _draw_eddie_brand_pdf(c, front_x0 + TRIM / 2, BLEED + TRIM * 0.58, r=TRIM * 0.18)

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 44)
    c.drawCentredString(front_x0 + TRIM / 2, BLEED + TRIM * 0.80, "EDDIE")

    c.setFont("Helvetica", 18)
    c.drawCentredString(front_x0 + TRIM / 2, BLEED + TRIM * 0.73, f"& {child_name}")

    c.setFont("Helvetica", 12)
    c.setFillColor(colors.grey)
    c.drawCentredString(front_x0 + TRIM / 2, BLEED + TRIM * 0.18, "Dein persönliches Malbuch aus echten Momenten")

    c.save()
    buf.seek(0)
    return buf.getvalue()


# =========================================================
# STRIPE (VERIFY session_id)
# =========================================================
def _stripe_ready() -> bool:
    return (stripe is not None) and bool(st.secrets.get("STRIPE_SECRET_KEY", ""))

def _verify_stripe_session_paid(session_id: str) -> bool:
    """Verify payment server-side with Stripe. Never trust URL param alone."""
    if not _stripe_ready():
        return False
    try:
        stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY", "")
        sess = stripe.checkout.Session.retrieve(session_id)
        payment_ok = (getattr(sess, "payment_status", "") == "paid")
        status_ok = (getattr(sess, "status", "") in ("complete", "paid"))
        return bool(payment_ok or status_ok)
    except Exception:
        return False


# =========================================================
# SESSION INIT
# =========================================================
for k in ["zip_bytes", "interior_pdf", "cover_pdf", "listing_txt", "cover_preview_png", "preflight", "is_paid"]:
    if k not in st.session_state:
        st.session_state[k] = None

if st.session_state.is_paid is None:
    st.session_state.is_paid = False

# Handle Stripe success redirect: ?session_id=...
session_id = st.query_params.get("session_id")
if session_id and not st.session_state.is_paid:
    with st.spinner("Zahlung wird verifiziert…"):
        if _verify_stripe_session_paid(str(session_id)):
            st.session_state.is_paid = True
            st.success("✅ Zahlung bestätigt. Download ist freigeschaltet.")
        else:
            st.warning("⚠️ Zahlung konnte nicht verifiziert werden. Bitte Checkout erneut öffnen.")

# =========================================================
# UI
# =========================================================
st.markdown(f'<div class="main-title">{APP_TITLE}</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Dein 1-Klick KDP-Publishing-Set: Interior + CoverWrap + Listing-Texte</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="kpi-container">'
    f'<span class="kpi">8.5" × 8.5"</span>'
    f'<span class="kpi">Bleed 0.125"</span>'
    f'<span class="kpi">{DPI} DPI Print-Ready</span>'
    '</div>',
    unsafe_allow_html=True
)

with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        child_name = st.text_input("Vorname des Kindes", value="Eddie", placeholder="z.B. Lukas")
    with col2:
        page_count = st.number_input("Seitenanzahl (Innen)", min_value=KDP_MIN_PAGES, max_value=300, value=DEFAULT_PAGES, step=1)

    paper_key = st.selectbox("Papier-Typ (Spine-Berechnung)", options=list(PAPER_FACTORS.keys()), index=0)

    eddie_mark_inside = st.toggle("Eddie-Branding auf Innenseiten", value=False)
    uploads = st.file_uploader("Fotos hochladen (min. 1)", accept_multiple_files=True, type=["jpg", "png"])

    st.caption("Tipp: Für maximale Abwechslung 12–24 Fotos. Für volle 300-DPI-Schärfe sollten Fotos ausreichend hoch aufgelöst sein.")
    st.markdown('</div>', unsafe_allow_html=True)

can_build = bool(child_name.strip()) and bool(uploads)

if st.button("🚀 Publishing-Paket generieren", disabled=not can_build):
    progress = st.progress(0, text="Starte Build…")
    with st.spinner("Erstelle Interior, CoverWrap, Listing & ZIP…"):
        progress.progress(15, text="Preflight-Check…")
        ok_ct, warn_ct, details = preflight_uploads_for_300dpi(uploads, target_inch=float((TRIM + 2 * BLEED) / inch))
        st.session_state.preflight = (ok_ct, warn_ct, details)

        progress.progress(40, text="Render: Interior PDF…")
        interior = build_interior_pdf(child_name.strip(), uploads, pages=int(page_count), eddie_mark_inside=eddie_mark_inside)

        progress.progress(65, text="Render: CoverWrap PDF…")
        cover = build_cover_wrap_pdf(child_name.strip(), page_count=int(page_count), paper_key=paper_key)

        progress.progress(75, text="Erzeuge Cover-Vorschau…")
        preview_png = build_front_cover_preview_png(child_name.strip(), size_px=900)

        progress.progress(85, text="Erzeuge Listing-Bundle…")
        listing_txt = build_listing_text(child_name.strip())

        progress.progress(95, text="Packe ZIP…")
        zip_buf = io.BytesIO()
        today = datetime.now().date().isoformat()
        base = _sanitize_filename(child_name.strip())

        with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"Interior_{base}_{today}.pdf", interior)
            z.writestr(f"CoverWrap_{base}_{today}.pdf", cover)
            z.writestr(f"Listing_{base}_{today}.txt", listing_txt)

        zip_buf.seek(0)

        st.session_state.interior_pdf = interior
        st.session_state.cover_pdf = cover
        st.session_state.cover_preview_png = preview_png
        st.session_state.listing_txt = listing_txt
        st.session_state.zip_bytes = zip_buf.getvalue()

        progress.progress(100, text="Fertig ✅")

    st.success("Assets erfolgreich generiert!")

# =========================================================
# PREVIEW + DOWNLOADS + LISTING
# =========================================================
if st.session_state.zip_bytes:
    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.markdown("### 👀 Vorschau & Qualitätscheck")
    colA, colB = st.columns(2, gap="large")

    with colA:
        if st.session_state.cover_preview_png:
            st.image(st.session_state.cover_preview_png, caption="Front-Cover Vorschau", use_container_width=True)

    with colB:
        st.markdown("**Preflight:**")
        st.success("✅ Output: 300 DPI Print-Standard")
        st.success(f"✅ Seiten: {int(page_count)}")

        pf = st.session_state.preflight
        if pf:
            ok_ct, warn_ct, _details = pf
            if warn_ct > 0:
                st.warning(f"⚠️ {warn_ct} Foto(s) evtl. zu klein für volle 300-DPI Full-Bleed-Schärfe. "
                           "Empfehlung: Originale aus der Kamera/WhatsApp-Originale verwenden.")
            else:
                st.success(f"✅ Foto-Auflösung: {ok_ct}/{ok_ct} OK für Full-Bleed")

        if len(uploads) < 12:
            st.info("💡 Tipp: Mehr Fotos = mehr Abwechslung im Buch.")
        else:
            st.success("✅ Foto-Varianz: sehr gut")

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.markdown("### 📥 Downloads")

    # Paywall UI
    if PAYWALL_MODE == "soft":
        st.download_button(
            "📦 Download: Komplettpaket (ZIP)",
            data=st.session_state.zip_bytes,
            file_name=f"Eddie_Publishing_Set_{_sanitize_filename(child_name.strip())}_{datetime.now().date().isoformat()}.zip",
            mime="application/zip",
        )

        st.caption("PWYW optional. Wenn du Eddie unterstützen willst: Premium/Support via Stripe.")
        pay_url = st.secrets.get("STRIPE_PAYMENT_LINK_URL", "")
        if pay_url:
            st.link_button("💜 Premium / Support (Stripe)", pay_url)

    elif PAYWALL_MODE == "hard":
        if st.session_state.is_paid:
            st.download_button(
                "📦 Download: Komplettpaket (ZIP) – freigeschaltet",
                data=st.session_state.zip_bytes,
                file_name=f"Eddie_Publishing_Set_{_sanitize_filename(child_name.strip())}_{datetime.now().date().isoformat()}.zip",
                mime="application/zip",
            )
        else:
            st.info("🔒 Vollständiges ZIP ist Premium. Nach Stripe-Checkout wird der Download automatisch freigeschaltet.")
            pay_url = st.secrets.get("STRIPE_PAYMENT_LINK_URL", "")
            if pay_url:
                st.link_button("🔓 Unlock Full ZIP (Stripe Checkout)", pay_url)
            else:
                st.error("Stripe Payment Link fehlt. Hinterlege STRIPE_PAYMENT_LINK_URL in Secrets.")

    # Individual downloads (always helpful)
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.markdown("### 📄 Einzeldateien (optional)")
    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "📘 Interior PDF",
            data=st.session_state.interior_pdf,
            file_name=f"Interior_{_sanitize_filename(child_name.strip())}.pdf",
            mime="application/pdf",
        )
    with d2:
        st.download_button(
            "🎨 CoverWrap PDF",
            data=st.session_state.cover_pdf,
            file_name=f"CoverWrap_{_sanitize_filename(child_name.strip())}.pdf",
            mime="application/pdf",
        )

    # Marketing expander
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    with st.expander("📦 Ready-to-Publish Amazon KDP Paket (Copy & Paste)", expanded=True):
        st.info("Kopiere diese Texte direkt in dein Amazon KDP Listing.")
        st.code(st.session_state.listing_txt or "", language="text")

        st.markdown("**Empfohlene A+ Content Strategie:**")
        st.markdown(
            "1. Foto vs. Skizze Vergleich (Transformation)\n"
            "2. Eddie als Brand-Charakter vorstellen (B/W + purpur Zunge)\n"
            "3. Detailansicht der Linien (300 DPI Qualitäts-Signal)\n"
        )

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    f'<div class="footer">Eddie’s Welt © 2026 • <a href="{HUB_URL}" target="_blank">Zum Strategie-Hub</a></div>',
    unsafe_allow_html=True
)
