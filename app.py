# app.py
# ==========================================================
# Quest-Logbuch Generator (Streamlit)
# - nutzt quest_data.py als Quest-Datenbank
# - generiert PDF mit Quest-HUD (Zone/Time oben, Mission/XP unten)
# ==========================================================

import streamlit as st
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

from quest_data import get_zones, pick_mission

st.set_page_config(page_title="Quest-Logbuch Generator", page_icon="📘", layout="centered")

# ---------------------------
# Layout Konstanten
# ---------------------------
PAGE_SIZE = A4
M_L, M_R, M_T, M_B = 16 * mm, 16 * mm, 16 * mm, 16 * mm

HUD_TOP_H = 14 * mm
HUD_BOTTOM_H = 18 * mm

def draw_hud(c: canvas.Canvas, w: float, h: float, zone_name: str, zone_tagline: str,
             session_time: str, mission_title: str, mission_xp: int):
    # Top HUD bar
    c.setLineWidth(1)
    c.rect(M_L, h - M_T - HUD_TOP_H, w - M_L - M_R, HUD_TOP_H)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(M_L + 4*mm, h - M_T - 9*mm, f"ZONE: {zone_name}")
    c.setFont("Helvetica", 9)
    c.drawString(M_L + 4*mm, h - M_T - 13*mm, zone_tagline[:80])

    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(w - M_R - 4*mm, h - M_T - 9*mm, f"TIME: {session_time}")

    # Bottom HUD bar
    c.rect(M_L, M_B, w - M_L - M_R, HUD_BOTTOM_H)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(M_L + 4*mm, M_B + 11*mm, f"MISSION: {mission_title[:70]}")
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(w - M_R - 4*mm, M_B + 11*mm, f"+{mission_xp} XP")

def draw_task_block(c: canvas.Canvas, w: float, h: float, title: str, body: str, page_no: int):
    # Content area between HUDs
    top_y = h - M_T - HUD_TOP_H - 6*mm
    bottom_y = M_B + HUD_BOTTOM_H + 8*mm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(M_L, top_y, title[:80])

    c.setFont("Helvetica", 11)
    y = top_y - 8*mm
    for line in body.split("\n"):
        if y < bottom_y:
            break
        c.drawString(M_L, y, line[:120])
        y -= 6*mm

    # Workspace box
    box_h = (y - bottom_y) - 6*mm
    if box_h > 40*mm:
        c.setLineWidth(1)
        c.rect(M_L, bottom_y, w - M_L - M_R, box_h)

    # Page number
    c.setFont("Helvetica", 9)
    c.drawRightString(w - M_R, 6*mm, f"{page_no}")

def make_pdf(title: str, pages: int, zone_id: str, difficulty: int, session_time: str, seed: int):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=PAGE_SIZE)
    w, h = PAGE_SIZE

    zones = get_zones()
    zone_name = next((z["name"] for z in zones if z["id"] == zone_id), zones[0]["name"])
    zone_tagline = next((z["tagline"] for z in zones if z["id"] == zone_id), zones[0]["tagline"])

    # Title page (Page 1)
    mission = pick_mission(zone_id, difficulty, seed + 1)
    draw_hud(c, w, h, zone_name, zone_tagline, session_time, mission.title, mission.xp)
    draw_task_block(
        c, w, h,
        title="Quest-Logbuch",
        body=(
            f"Titel: {title}\n"
            f"Prinzip: Es gibt ein Ziel – aber mehrere gültige Wege.\n"
            f"Regel: Kein Wettbewerb. Helfen ist Fortschritt.\n\n"
            f"Start-Mission:\n"
            f"- Bewegung: {mission.movement}\n"
            f"- Denken: {mission.thinking}\n"
            f"- Nachweis: {mission.proof}"
        ),
        page_no=1
    )
    c.showPage()

    # Content pages (Pages 2..pages)
    for p in range(2, pages + 1):
        mission = pick_mission(zone_id, difficulty, seed + p)
        draw_hud(c, w, h, zone_name, zone_tagline, session_time, mission.title, mission.xp)

        body = (
            f"Bewegung:\n- {mission.movement}\n\n"
            f"Denken (Ziel + mehrere Wege):\n- {mission.thinking}\n\n"
            f"Checkpoint:\n- {mission.proof}\n"
        )

        draw_task_block(c, w, h, title=f"Aufgabe {p-1}", body=body, page_no=p)
        c.showPage()

    c.save()
    return buf.getvalue()

# ---------------------------
# UI
# ---------------------------
st.title("📘 Quest-Logbuch Generator")

st.caption("Druck-PDF mit Quest-HUD: Zone+Time oben, Mission+XP unten. Kein Wettbewerb. Mehrere Wege sind richtig.")

with st.form("quest_form"):
    title = st.text_input("Buchtitel", value="Denken & Bewegung – Quest-Logbuch")
    pages = st.selectbox("Seiten (KDP: 24)", [24, 16, 8], index=0)
    zone_id = st.selectbox("Zone", [z["id"] for z in get_zones()],
                           format_func=lambda zid: next(z["name"] for z in get_zones() if z["id"] == zid))
    difficulty = st.slider("Schwierigkeit (1–5)", 1, 5, 3)
    session_time = st.text_input("Session Time (HUD)", value="10:00")
    seed = st.number_input("Seed (Reproduzierbarkeit)", min_value=0, max_value=999999, value=1234, step=1)
    submitted = st.form_submit_button("📄 PDF generieren")

if submitted:
    pdf = make_pdf(title=title.strip(), pages=int(pages), zone_id=zone_id, difficulty=int(difficulty),
                   session_time=session_time.strip(), seed=int(seed))

    st.success("Fertig. Quest-Logbuch ist generiert.")
    st.download_button(
        "⬇️ PDF herunterladen",
        data=pdf,
        file_name="quest_logbook.pdf",
        mime="application/pdf",
        use_container_width=True
    )
