import streamlit as st
import cv2
import numpy as np
import os
import random
import tempfile
import re
from pathlib import Path
import qrcode
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.units import inch

# --- 1) SMART HELPERS (EXIF & SORT) ---

def _exif_datetime(file_obj) -> str:
    """Extrahiert das Aufnahmedatum aus EXIF-Daten."""
    try:
        file_obj.seek(0)
        img = Image.open(file_obj)
        exif = img.getexif()
        # 36867 = DateTimeOriginal, 306 = DateTime
        dt = exif.get(36867) or exif.get(306)
        file_obj.seek(0)
        return str(dt) if dt else ""
    except Exception:
        try: file_obj.seek(0)
        except: pass
        return ""

def sort_uploads_smart(uploaded_list):
    """Sortiert nach Zeitstempel, falls vorhanden, sonst nach Upload-Reihenfolge."""
    if not uploaded_list: return []
    items = []
    for idx, f in enumerate(uploaded_list):
        dt = _exif_datetime(f)
        items.append({'dt': dt, 'idx': idx, 'file': f})
    
    # Sortier-Logik: Falls EXIF vorhanden, gewichtet das Zeitdatum, sonst die Index-Position
    # (Bilder ohne Datum kommen nach unten)
    items.sort(key=lambda x: (x['dt'] == "", x['dt'], x['idx']))
    return [item['file'] for item in items]

def _safe_filename(name: str) -> str:
    base = Path(name).name
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
    return base if base else "upload.jpg"

def foto_zu_skizze(input_path, output_path):
    try:
        img = cv2.imread(input_path)
        if img is None: return False
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        inverted = 255 - gray
        blurred = cv2.GaussianBlur(inverted, (21, 21), 0)
        inverted_blurred = 255 - blurred
        sketch = cv2.divide(gray, inverted_blurred, scale=256.0)
        sketch = cv2.normalize(sketch, None, 0, 255, cv2.NORM_MINMAX)
        cv2.imwrite(output_path, sketch)
        return True
    except: return False

# --- 2) ZEICHEN-FUNKTIONEN ---

def zeichne_suchspiel(c, width, y_start, img_height, anzahl):
    form = random.choice(["kreis", "viereck", "dreieck"])
    c.setLineWidth(2); c.setStrokeColor(colors.black); c.setFillColor(colors.white)
    y_min, y_max = int(y_start), int(y_start + img_height - 30)
    for _ in range(anzahl):
        x = random.randint(50, int(width) - 50)
        y = random.randint(y_min, y_max) if y_max > y_min else y_min
        s = random.randint(15, 25)
        if form == "kreis": c.circle(x, y, s / 2, fill=1, stroke=1)
        elif form == "viereck": c.rect(x - s / 2, y - s / 2, s, s, fill=1, stroke=1)
        else:
            p = c.beginPath()
            p.moveTo(x, y + s / 2); p.lineTo(x - s / 2, y - s / 2); p.lineTo(x + s / 2, y - s / 2); p.close()
            c.drawPath(p, fill=1, stroke=1)
    
    legend_y = max(50, y_start - 30)
    c.setFillColor(colors.white)
    if form == "kreis": c.circle(80, legend_y + 5, 8, fill=0, stroke=1)
    elif form == "viereck": c.rect(72, legend_y - 3, 16, 16, fill=0, stroke=1)
    else: 
        p = c.beginPath()
        p.moveTo(80, legend_y + 13); p.lineTo(72, legend_y - 3); p.lineTo(88, legend_y - 3); p.close()
        c.drawPath(p, fill=0, stroke=1)
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 16)
    c.drawString(100, legend_y, f"x {anzahl}")

def zeichne_fortschritt(c, width, stunde, y=40, margin=50):
    step = (width - 2 * margin) / 23
    c.setLineWidth(2); c.setStrokeColor(colors.gray); c.line(margin, y, width - margin, y)
    for i in range(24):
        cx = margin + i * step
        if i < stunde:
            c.setFillColor(colors.black); c.circle(cx, y, 4, fill=1, stroke=0)
        elif i == stunde:
            c.setFillColor(colors.white); c.setStrokeColor(colors.black); c.setLineWidth(3); c.circle(cx, y, 8, fill=1, stroke=1)
        else:
            c.setFillColor(colors.white); c.setStrokeColor(colors.lightgrey); c.setLineWidth(1); c.circle(cx, y, 3, fill=1, stroke=1)

def _draw_qr(c, url, x, y, size):
    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        img_qr.save(tmp.name)
        c.drawImage(tmp.name, x, y, width=size, height=size)
    os.unlink(tmp.name)

# --- 3) UI ---

st.set_page_config(page_title="Eddie's Welt", layout="centered")
st.title("✏️ Eddie's Welt")
st.caption("Ein Malbuch aus deinem Tag. Privat & Sicher.")

with st.sidebar:
    st.header("Einstellungen")
    kdp_mode = st.toggle('📦 KDP-Druckversion (8.5"x8.5")', value=False)
    app_url = st.text_input("App-Link für QR", "https://eddie-welt.streamlit.app")
    st.divider()
    st.info("Bilder werden automatisch chronologisch sortiert (EXIF).")

kind_name = st.text_input("Wie heißt das Kind?", "Eddie").strip()
uploaded_raw = st.file_uploader("Wähle bis zu 24 Fotos:", accept_multiple_files=True, type=["jpg", "jpeg", "png"])

if uploaded_raw:
    # --- SMART SORT ---
    uploaded_files = sort_uploads_smart(uploaded_raw[:24])
    
    with st.expander("👀 Vorschau Reihenfolge (Chronologisch sortiert)"):
        for i, f in enumerate(uploaded_files, start=1):
            st.text(f"{i:02d}. {f.name}")

    if st.button("Buch binden", use_container_width=True):
        status = st.empty()
        status.info("Das Buch wird gebunden...")

        with tempfile.TemporaryDirectory() as temp_dir:
            raw_paths = []
            seed_material_list = []
            
            for idx, up in enumerate(uploaded_files):
                safe = _safe_filename(up.name)
                p = os.path.join(temp_dir, f"{idx:03d}_{safe}")
                with open(p, "wb") as f: f.write(up.getbuffer())
                raw_paths.append(p)
                seed_material_list.append(f"{safe}:{up.size}")

            # Reproduzierbarer Seed
            seed_material = kind_name + "|" + "|".join(seed_material_list)
            random.seed(seed_material.encode("utf-8", errors="ignore"))

            # PDF Setup
            if kdp_mode:
                w, h = 8.5 * inch, 8.5 * inch
                m = 0.375 * inch
            else:
                w, h = A4
                m = 50
            
            pdf_path = os.path.join(temp_dir, "buch.pdf")
            c = canvas.Canvas(pdf_path, pagesize=(w, h))

            # Cover & Manifest
            c.setFont("Helvetica-Bold", 36); c.drawCentredString(w/2, h/2+20, f"{kind_name.upper()}S REISE"); c.showPage()
            c.setFont("Helvetica-Bold", 24); c.drawCentredString(w/2, h-120, f"Hallo {kind_name}.")
            c.setFont("Helvetica", 14); y_txt = h-200
            for l in ["Das ist deine Welt.", "Hier gibt es kein Falsch.", "Nimm deinen Stift.", "Leg los."]:
                c.drawCentredString(w/2, y_txt, l); y_txt -= 30
            c.showPage()

            # Seiten generieren
            for i, p_path in enumerate(raw_paths):
                c.setFont("Helvetica-Bold", 30); c.drawCentredString(w/2, h-60, f"{i:02d}:00 Uhr")
                out_skizze = os.path.join(temp_dir, f"sk_{i}.jpg")
                if foto_zu_skizze(p_path, out_skizze):
                    img_w, img_h = w - 2*m, h - 2*m - 160
                    c.drawImage(out_skizze, m, m+100, width=img_w, height=img_h, preserveAspectRatio=True)
                    zeichne_suchspiel(c, w, m+100, img_h, random.randint(3,6))
                zeichne_fortschritt(c, w, i, y=m+30, margin=m)
                c.showPage()

            # Solidarity QR & Urkunde
            if kdp_mode:
                c.setFont("Helvetica-Bold", 18); c.drawCentredString(w/2, h-100, "Teile die Magie!")
                _draw_qr(c, app_url, (w-120)/2, h/2-60, 120)
                c.showPage()

            c.rect(m, m, w-2*m, h-2*m)
            c.setFont("Helvetica-Bold", 30); c.drawCentredString(w/2, h/2, "FÜR DEN ENTDECKER"); c.showPage()
            c.save()

            status.success("Buch fertig!")
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Buch herunterladen", f.read(), file_name=f"{kind_name}_Welt.pdf", use_container_width=True)
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Buch herunterladen", f.read(), file_name=f"{kind_name}_Welt.pdf")
