# app.py
import streamlit as st
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

from quest_data import zone_for_hour, pick_mission, fmt_hour

st.set_page_config(page_title="Quest-Logbuch Generator", page_icon="📘", layout="centered")

# ---------------- HUD LAYOUT ----------------
PAGE_SIZE = A4
M_L, M_R, M_T, M_B = 16*mm, 16*mm, 16*mm, 16*mm
HUD_TOP_H = 14*mm
HUD_BOTTOM_H = 18*mm


def draw_hud(c: canvas.Canvas, w: float, h: float, zone_name: str, zone_line: str, time_str: str,
             mission_title: str, xp: int, difficulty: int, page_no: int):
    # Top bar
    c.setLineWidth(1)
    c.rect(M_L, h - M_T - HUD_TOP_H, w - M_L - M_R, HUD_TOP_H)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(M_L + 4*mm, h - M_T - 9*mm, f"ZONE: {zone_name}")
    c.setFont("Helvetica", 9)
    c.drawString(M_L + 4*mm, h - M_T - 13*mm, zone_line[:90])

    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(w - M_R - 4*mm, h - M_T - 9*mm, f"TIME: {time_str}")

    # Bottom bar
    c.rect(M_L, M_B, w - M_L - M_R, HUD_BOTTOM_H)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(M_L + 4*mm, M_B + 11*mm, f"MISSION: {mission_title[:70]}")
    c.drawRightString(w - M_R - 4*mm, M_B + 11*mm, f"+{xp} XP")

    c.setFont("Helvetica", 9)
    c.drawString(M_L + 4*mm, M_B + 4*mm, f"DIFF: {difficulty}/5")
    c.drawRightString(w - M_R - 4*mm, M_B + 4*mm, f"PAGE: {page_no}")


def draw_mission_text(c: canvas.Canvas, w: float, h: float, movement: str, thinking: str, proof: str):
    # Small text block above bottom HUD
    y = M_B + HUD_BOTTOM_H + 8*mm
    c.setFont("Helvetica", 10)
    lines = [
        "Bewegung:",
        f"- {movement}",
        "",
        "Denken (Ziel + mehrere Wege):",
        f"- {thinking}",
        "",
        "Checkpoint:",
        f"- {proof}",
    ]
    for line in lines:
        if y > h - M_T - HUD_TOP_H - 10*mm:
            break
        c.drawString(M_L, y, line[:120])
        y += 5*mm


def parse_start_hour(s: str) -> int:
    s = (s or "").strip()
    if not s:
        return 6
    if ":" in s:
        return int(s.split(":", 1)[0]) % 24
    return int(s) % 24


# ---------------- ENGINE AUTO-LOADER ----------------
def _try_import_engine():
    """
    Tries to find an existing drawing function in your repo.
    Returns a callable or None.
    Expected signatures (we try multiple):
      fn(c, page_index, page_width, page_height, seed=..., **kwargs)
    """
    candidates = [
        ("legacy.generate_book", "draw_page"),
        ("legacy.generate_book", "render_activity_page"),
        ("generate_book", "draw_page"),
        ("generate_book", "render_activity_page"),
    ]
    for mod_name, fn_name in candidates:
        try:
            mod = __import__(mod_name, fromlist=[fn_name])
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                return fn, f"{mod_name}.{fn_name}"
        except Exception:
            continue
    return None, None


ENGINE_FN, ENGINE_NAME = _try_import_engine()


def render_base_page(c: canvas.Canvas, w: float, h: float, page_index: int, seed: int):
    """
    Draws the underlying sketch/activity page using your existing engine if available,
    otherwise falls back to a placeholder.
    """
    if ENGINE_FN:
        # Try calling with flexible params
        try:
            ENGINE_FN(c, page_index=page_index, page_width=w, page_height=h, seed=seed)
            return True
        except TypeError:
            pass
        try:
            ENGINE_FN(c, page_index, w, h, seed=seed)
            return True
        except TypeError:
            pass
        try:
            ENGINE_FN(c, page_index, w, h)
            return True
        except Exception:
            pass

    # Fallback placeholder
    c.setFont("Helvetica-Bold", 16)
    c.drawString(M_L, h - M_T - HUD_TOP_H - 12*mm, f"SKETCH PAGE {page_index} (Engine nicht gefunden)")
    c.setLineWidth(1)
    c.rect(M_L, M_B + HUD_BOTTOM_H + 30*mm, w - M_L - M_R, h - (M_B + HUD_BOTTOM_H + 60*mm))
    return False


# ---------------- PDF BUILD ----------------
def build_pdf(pages: int, start_hour: int, difficulty: int, seed: int):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=PAGE_SIZE)
    w, h = PAGE_SIZE

    for p in range(1, pages + 1):
        hour = (start_hour + (p - 1)) % 24
        zone = zone_for_hour(hour)
        mission = pick_mission(hour=hour, difficulty=difficulty, seed=seed + p)

        # 1) Base page (your engine)
        render_base_page(c, w, h, page_index=p, seed=seed + p)

        # 2) HUD overlay last
        time_str = fmt_hour(hour)
        zone_line = f"{zone.quest_type} · {zone.atmosphere}"
        draw_hud(c, w, h, zone.name, zone_line, time_str, mission.title, mission.xp, difficulty, p)

        # Mission text
        draw_mission_text(c, w, h, mission.movement, mission.thinking, mission.proof)

        c.showPage()

    c.save()
    return buf.getvalue()


# ---------------- UI ----------------
st.title("📘 Quest-Logbuch Generator")
if ENGINE_NAME:
    st.caption(f"Engine erkannt: {ENGINE_NAME} ✅  |  HUD aktiv.")
else:
    st.caption("Engine nicht erkannt (Fallback-Box) ⚠️  |  HUD aktiv.")

with st.form("f"):
    pages = st.selectbox("Seiten (KDP: 24)", [24, 16, 8], index=0)
    start_time = st.text_input("Startzeit (Stunde oder HH:MM)", value="06:00")
    difficulty = st.slider("Schwierigkeit (1–5)", 1, 5, 3)
    seed = st.number_input("Seed (Reproduzierbarkeit)", min_value=0, max_value=999999, value=1234, step=1)
    go = st.form_submit_button("📄 PDF generieren")

if go:
    start_hour = parse_start_hour(start_time)
    pdf = build_pdf(int(pages), int(start_hour), int(difficulty), int(seed))

    st.download_button(
        "⬇️ PDF herunterladen",
        data=pdf,
        file_name="quest_logbook.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
