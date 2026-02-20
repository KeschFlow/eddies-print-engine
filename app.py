# =========================================================
# app.py — E. P. E. Eddie's Print Engine — v5.10.2 FINAL
#
# v5.10.2:
# - Streamlit Cloud Fix: runtime.txt pin (Python 3.11) for OpenCV wheels
# - Kid Time Guidance: every hour has its own header color (24 distinct hues via quest_data.py)
# - QR CTA OUTRO: vector QR (print-sharp) to https://keschflow.github.io/start/
# =========================================================

from __future__ import annotations

import io
import os
import gc
import time
import math
import secrets
import hashlib
import sqlite3
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from collections import OrderedDict

import streamlit as st
import cv2
import numpy as np
import stripe
from PIL import Image, ImageDraw, ImageFile

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth

# ✅ Vector QR (KDP-sharp)
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

import image_wash as iw

# --- PIL Hardening ---
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = 25_000_000  # ~25MP

# =========================================================
# HELPERS
# =========================================================
def _qp(name: str) -> str:
    v = st.query_params.get(name, "")
    if isinstance(v, list):
        return v[0] if v else ""
    return v or ""

def _name_genitive(name: str) -> str:
    n = (name or "").strip()
    if not n:
        return "Deins"
    low = n.lower()
    if low.endswith(("s", "ß", "x", "z")):
        return f"{n}'"
    return f"{n}s"

# =========================================================
# RATE LIMITING (SQLite local - Self Healing)
# =========================================================
DB_PATH = "fair_use.db"

def _init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS builds (id INTEGER PRIMARY KEY AUTOINCREMENT, ip TEXT, timestamp REAL)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_builds_ip_ts ON builds(ip, timestamp)")
    cutoff = time.time() - (7 * 24 * 3600)
    c.execute("DELETE FROM builds WHERE timestamp < ?", (cutoff,))
    conn.commit()
    conn.close()

def _get_client_ip() -> str:
    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        if headers:
            xff = headers.get("X-Forwarded-For") or headers.get("x-forwarded-for")
            if xff:
                return xff.split(",")[0].strip()
    except Exception:
        pass
    try:
        from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx and getattr(ctx, "session_id", None):
            return f"session:{ctx.session_id}"
    except Exception:
        pass
    return "unknown"

def _get_build_count(ip: str, hours: int = 24) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff = time.time() - (hours * 3600)
    c.execute("SELECT COUNT(*) FROM builds WHERE ip=? AND timestamp>?", (ip, cutoff))
    row = c.fetchone()
    conn.close()
    return int(row[0] if row else 0)

def _log_build(ip: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO builds (ip, timestamp) VALUES (?, ?)", (ip, time.time()))
    conn.commit()
    conn.close()

_init_db()

# =========================================================
# ACCESS & LIMIT LOGIC
# =========================================================
STRIPE_SECRET = st.secrets.get("STRIPE_SECRET_KEY", "")
PAYMENT_LINK = st.secrets.get("STRIPE_PAYMENT_LINK", "https://buy.stripe.com/...")

FREE_LIMIT = 3
COMMUNITY_TOKENS = {"KITA-2026": 50, "SCHULE-X": 50, "THERAPIE-EDDIE": 100}

client_ip = _get_client_ip()
builds_used = _get_build_count(client_ip)

user_limit = FREE_LIMIT
is_supporter = False
access_mode = "Free"

st.session_state.setdefault("community_pass", "")
community_pass = _qp("pass") or st.session_state["community_pass"]

if community_pass in COMMUNITY_TOKENS:
    user_limit = int(COMMUNITY_TOKENS[community_pass])
    access_mode = "Community"

session_id = _qp("session_id")
if session_id and STRIPE_SECRET:
    stripe.api_key = STRIPE_SECRET
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if getattr(session, "status", "") == "complete" and getattr(session, "payment_status", "") == "paid":
            is_supporter = True
            user_limit = 9999
            access_mode = "Supporter"
    except Exception:
        pass

if not STRIPE_SECRET and not community_pass and not session_id:
    access_mode = "Dev Mode"
    user_limit = 9999

builds_left = max(0, user_limit - builds_used)
can_build_limit = builds_left > 0 or is_supporter

# =========================================================
# QUEST SYSTEM ZONES (world-building; optional quest_data.py)
# =========================================================
try:
    import quest_data as qd
except Exception as e:
    qd = None
    _QD_IMPORT_ERROR = str(e)

@dataclass(frozen=True)
class ZoneStub:
    name: str
    icon: str
    quest_type: str
    atmosphere: str

def _zone_stub(hour: int) -> ZoneStub:
    if 6 <= hour <= 10:
        return ZoneStub("Morgen-Start", "🌤️", "Warm-up", "ruhig")
    if 11 <= hour <= 15:
        return ZoneStub("Mittags-Mission", "🌞", "Action", "wach")
    if 16 <= hour <= 20:
        return ZoneStub("Nachmittags-Boost", "🟣", "Abenteuer", "spielerisch")
    return ZoneStub("Abend-Ruhe", "🌙", "Runterfahren", "sanft")

def _get_zone_for_hour(hour: int) -> ZoneStub:
    if qd and hasattr(qd, "get_zone_for_hour"):
        try:
            z = qd.get_zone_for_hour(hour)
            return ZoneStub(
                getattr(z, "name", "Zone"),
                getattr(z, "icon", "🟣"),
                getattr(z, "quest_type", "Quest"),
                getattr(z, "atmosphere", ""),
            )
        except Exception:
            pass
    return _zone_stub(hour)

def _get_hour_color(hour: int) -> Tuple[float, float, float]:
    """
    ✅ Stundenfarbe:
    - Wenn quest_data.py vorhanden: 24 definierte Farben (oder Gradient) pro Stunde
    - Sonst: Fallback Verlauf
    """
    if qd and hasattr(qd, "get_hour_color"):
        try:
            rgb = qd.get_hour_color(hour)
            if isinstance(rgb, (tuple, list)) and len(rgb) >= 3:
                return float(rgb[0]), float(rgb[1]), float(rgb[2])
        except Exception:
            pass
    t = (hour % 24) / 24.0
    return (0.45 + 0.25 * (1 - t), 0.2 + 0.15 * t, 0.9 - 0.25 * t)

def _fmt_hour(hour: int) -> str:
    if qd and hasattr(qd, "fmt_hour"):
        try:
            return str(qd.fmt_hour(hour))
        except Exception:
            pass
    return f"{int(hour):02d}:00"

# =========================================================
# DYNAMIC QUEST BANK (240 unique quests + fallback)
# =========================================================
def _build_full_quest_bank():
    bank = {}

    m_titles = ["Start-Kraft", "Rüstung anlegen", "Morgen-Fokus", "Wachmacher", "Sonnen-Sucher", "Frühsport", "Augen auf", "Energie-Tank", "Tag-Blick", "Morgen-Scan"]
    m_moves = ["Mache 10 Kniebeugen.", "20 Sekunden Hampelmann.", "Streck dich so groß du kannst.", "Laufe 10 Sekunden auf der Stelle.", "Hüpfe 5x hoch in die Luft.", "Berühre 10x deine Zehenspitzen.", "Kreise deine Arme wie Windmühlen.", "Mache 5 Froschsprünge.", "Balanciere 10 Sekunden auf einem Bein.", "Mache 3 große Ausfallschritte."]

    d_titles = ["Musterjäger", "Adlerauge", "Action-Check", "Spürhund", "Fokus-Meister", "Abenteuer-Blick", "Such-Ninja", "Formen-Ritter", "Tempo-Scan", "Durchblick"]
    d_moves = ["Mache 10 Hampelmänner.", "Hüpfe 10x auf dem rechten Bein.", "Mache 5 Kniebeugen.", "Laufe im Zickzack.", "Dreh dich 5x im Kreis.", "Mache 5 Känguru-Sprünge.", "Balanciere wie ein Flamingo.", "Mache 10 schnelle Schritte auf der Stelle.", "Streck dich und berühre den Boden.", "Mache 3 Sternensprünge."]

    e_titles = ["Nacht-Wache", "Ruhe-Check", "Schatten-Jäger", "Leise Pfoten", "Dämmerungs-Blick", "Abend-Fokus", "Sternen-Scanner", "Fokus-Ninja", "Traum-Pfad", "Nacht-Auge"]
    e_moves = ["Stell dich auf die Zehenspitzen und zähle bis 10.", "Bewege dich 10 Sekunden in Zeitlupe.", "Atme 3x tief ein und aus.", "Setz dich in den Schneidersitz.", "Massiere sanft deine Ohren.", "Mache dich ganz klein wie ein Igel.", "Streck dich langsam nach oben.", "Kreise sanft deine Schultern.", "Schließe die Augen und zähle bis 5.", "Stell dich aufrecht hin wie ein Baum."]

    n_titles = ["Traum-Fänger", "Stille Wacht", "Nacht-Flug", "Schlaf-Ninja", "Mondlicht-Blick", "Traum-Scan", "Sternen-Staub", "Leise Suche", "Ruhe-Mission", "Nacht-Fokus"]
    n_moves = ["Atme tief in den Bauch.", "Lege dich 10 Sekunden ganz still hin.", "Bewege deine Finger wie Sterne.", "Schließe die Augen und atme.", "Sei so leise wie eine Maus.", "Strecke deine Arme sanft aus.", "Mache ein leises 'Schh'-Geräusch.", "Gähne einmal herzhaft.", "Lächle mit geschlossenen Augen.", "Entspanne deine Schultern."]

    proofs = ["Kreise alle Formen ein.", "Male die Sterne gelb aus.", "Setze einen Punkt in jede Form.", "Verbinde die Formen mit einer Linie.", "Zähle laut mit und hake ab.", "Male die Quadrate bunt an.", "Setze einen Haken neben die Dreiecke.", "Male kleine Gesichter in die Formen."]

    for h in range(24):
        hour_str = f"{h:02d}"
        bank[hour_str] = []

        if 6 <= h <= 11:
            t_list, m_list = m_titles, m_moves
        elif 12 <= h <= 17:
            t_list, m_list = d_titles, d_moves
        elif 18 <= h <= 21:
            t_list, m_list = e_titles, e_moves
        else:
            t_list, m_list = n_titles, n_moves

        for i in range(10):
            q_id = f"{hour_str}_{i:02d}"
            if i % 3 == 0:
                thinking = "Finde {tri} Dreiecke, {sq} Quadrate und {st_} Sterne."
            elif i % 3 == 1:
                thinking = "Spüre insgesamt {total} versteckte Formen auf (△, □, ★)."
            else:
                thinking = "Suche: {tri}x Dreieck, {sq}x Quadrat, {st_}x Stern."

            bank[hour_str].append({
                "id": q_id,
                "title": t_list[i % len(t_list)],
                "xp": 10 + i + (h % 5),
                "movement": m_list[i % len(m_list)],
                "thinking": thinking,
                "proof": proofs[(h + i) % len(proofs)]
            })

    reserve = []
    for i in range(24):
        reserve.append({
            "id": f"res_{i:02d}",
            "title": "Sonder-Mission",
            "xp": 20,
            "movement": "Mache 3x tief Ooommm.",
            "thinking": "Finde {total} versteckte Symbole.",
            "proof": "Setze einen dicken Haken!"
        })

    return bank, reserve

QUEST_BANK, QUEST_RESERVE = _build_full_quest_bank()

def build_book_schedule(seed: int, start_hour: int, count: int) -> dict:
    rng = np.random.default_rng(seed)
    used_ids = set()
    schedule = {}

    for i in range(count):
        hour = (start_hour + i) % 24
        hour_str = f"{hour:02d}"
        candidates = [q for q in QUEST_BANK.get(hour_str, []) if q["id"] not in used_ids]

        if not candidates:
            candidates = [q for q in QUEST_RESERVE if q["id"] not in used_ids]

        if not candidates:
            candidates = QUEST_RESERVE

        idx = rng.integers(0, len(candidates))
        picked = candidates[idx]
        used_ids.add(picked["id"])
        schedule[hour] = picked

    return schedule

@dataclass
class Mission:
    title: str
    xp: int
    movement: str
    thinking: str
    proof: str

# =========================================================
# CONFIG
# =========================================================
APP_TITLE = "E. P. E. Eddie's Print Engine"
APP_ICON = "🐶"

EDDIE_PURPLE = "#7c3aed"
DPI = 300
TRIM_IN = 8.5
TRIM = TRIM_IN * inch
BLEED = 0.125 * inch
SAFE_INTERIOR = 0.375 * inch

INK_BLACK = colors.Color(0, 0, 0)
INK_GRAY_70 = colors.Color(0.30, 0.30, 0.30)

PAPER_FACTORS = {
    "Schwarzweiß – Weiß": 0.002252,
    "Schwarzweiß – Creme": 0.0025,
    "Farbe – Weiß (Standard)": 0.002252
}
KDP_PAGES_FIXED = 26
SPINE_TEXT_MIN_PAGES = 79

MAX_SKETCH_CACHE = 256
MAX_WASH_CACHE = 64

BUILD_TAG = "v5.10.2-final"

# =========================================================
# CORE
# =========================================================
def _new_build_nonce() -> str:
    return f"{time.time_ns():x}-{secrets.token_hex(16)}"

def _imprint_nonce(c: canvas.Canvas, build_nonce: str) -> None:
    try:
        c.saveState()
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 1)
        c.drawString(-1000, -1000, f"nonce:{build_nonce}")
        c.restoreState()
    except Exception:
        pass

def _stable_seed(s: str) -> int:
    return int.from_bytes(hashlib.sha256(s.encode("utf-8")).digest()[:8], "big")

# =========================================================
# FONTS & TEXT
# =========================================================
def _try_register_fonts() -> Dict[str, str]:
    n = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    b = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(n):
        try:
            pdfmetrics.registerFont(TTFont("EDDIES_FONT", n))
        except Exception:
            pass
    if os.path.exists(b):
        try:
            pdfmetrics.registerFont(TTFont("EDDIES_FONT_BOLD", b))
        except Exception:
            pass
    return {
        "normal": "EDDIES_FONT" if "EDDIES_FONT" in pdfmetrics.getRegisteredFontNames() else "Helvetica",
        "bold": "EDDIES_FONT_BOLD" if "EDDIES_FONT_BOLD" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold",
    }

FONTS = _try_register_fonts()

def _set_font(c: canvas.Canvas, bold: bool, size: int) -> float:
    c.setFont(FONTS["bold"] if bold else FONTS["normal"], size)
    return size * 1.22

def _wrap_text_hard(text: str, font: str, size: int, max_w: float) -> List[str]:
    text = (text or "").strip()
    if not text:
        return [""]
    lines, cur = [], ""

    def fits(s: str) -> bool:
        return stringWidth(s, font, size) <= max_w

    for w in text.split():
        trial = (cur + " " + w).strip()
        if cur and fits(trial):
            cur = trial
        elif not cur and fits(w):
            cur = w
        else:
            if cur:
                lines.append(cur)
            if not fits(w):
                chunk = ""
                for ch in w:
                    if fits(chunk + ch):
                        chunk += ch
                    else:
                        if chunk:
                            lines.append(chunk)
                        chunk = ch
                cur = chunk
            else:
                cur = w
    if cur:
        lines.append(cur)
    return lines

def _fit_lines(lines: List[str], max_lines: int) -> List[str]:
    if len(lines) <= max_lines:
        return lines
    out = lines[:max_lines]
    out[-1] = (out[-1].rstrip()[:-3].rstrip() if len(out[-1]) > 3 else out[-1]) + "…"
    return out

def _kid_short(s: str, max_words: int = 4) -> str:
    s = (s or "").strip().replace("•", " ").replace("→", " ").replace("-", " ")
    return " ".join([w for w in s.split() if w and len(w) > 1][:max_words])

# =========================================================
# ICONS & SHAPES
# =========================================================
def _draw_eddie(c: canvas.Canvas, cx: float, cy: float, r: float, style: str = "tongue"):
    c.saveState()
    if style == "tongue":
        tw, th = r * 0.55, r * 0.70
        c.setFillColor(colors.HexColor(EDDIE_PURPLE))
        c.setStrokeColor(INK_BLACK)
        c.setLineWidth(max(1.2, r * 0.06))
        c.roundRect(cx - tw / 2, cy - th / 2, tw, th, r * 0.18, stroke=1, fill=1)
        c.setLineWidth(max(0.8, r * 0.03))
        c.line(cx, cy - th / 2 + th * 0.15, cx, cy - th / 2 + th * 0.45)
    else:
        c.setStrokeColor(INK_BLACK)
        c.setFillColor(colors.white)
        c.setLineWidth(max(1.2, r * 0.06))
        c.circle(cx, cy, r, stroke=1, fill=1)
        c.line(cx - r * 0.55, cy + r * 0.55, cx - r * 0.15, cy + r * 0.95)
        c.line(cx - r * 0.15, cy + r * 0.95, cx - r * 0.05, cy + r * 0.45)
        c.line(cx + r * 0.55, cy + r * 0.55, cx + r * 0.15, cy + r * 0.95)
        c.line(cx + r * 0.15, cy + r * 0.95, cx + r * 0.05, cy + r * 0.45)
        c.setFillColor(colors.HexColor(EDDIE_PURPLE))
        c.roundRect(cx - r * 0.12, cy - r * 0.45, r * 0.24, r * 0.28, r * 0.10, stroke=0, fill=1)
    c.restoreState()

@dataclass
class ShapeSpec:
    kind: str
    cx: float
    cy: float
    size: float
    rot: float

def _generate_shapes(pb_w: float, pb_h: float, seed: int) -> List[ShapeSpec]:
    rng = np.random.default_rng(seed)
    header_h = 0.75 * inch
    card_h = 2.85 * inch
    pad = 0.45 * inch

    min_x, max_x = pad, pb_w - pad
    min_y, max_y = card_h + pad, pb_h - header_h - pad
    if max_x <= min_x or max_y <= min_y:
        return []

    shapes = []
    for _ in range(int(rng.integers(3, 8))):
        shapes.append(ShapeSpec(
            kind=str(rng.choice(["triangle", "square", "star"])),
            cx=float(rng.uniform(min_x, max_x)),
            cy=float(rng.uniform(min_y, max_y)),
            size=float(rng.uniform(0.28, 0.58)) * inch,
            rot=float(rng.uniform(0, 360))
        ))
    return shapes

def _draw_shapes(c: canvas.Canvas, shapes: List[ShapeSpec]):
    if not shapes:
        return
    c.saveState()
    c.setStrokeColor(INK_BLACK)
    c.setLineWidth(2.2)
    c.setFillColor(colors.white)
    for s in shapes:
        c.saveState()
        c.translate(s.cx, s.cy)
        c.rotate(s.rot)
        if s.kind == "triangle":
            p = c.beginPath()
            p.moveTo(0, s.size / 2)
            p.lineTo(-s.size / 2, -s.size / 2)
            p.lineTo(s.size / 2, -s.size / 2)
            p.close()
            c.drawPath(p, fill=1, stroke=1)
        elif s.kind == "square":
            c.rect(-s.size / 2, -s.size / 2, s.size, s.size, fill=1, stroke=1)
        else:
            p = c.beginPath()
            r_out, r_in = s.size / 2, (s.size / 2) / 2.5
            for i in range(10):
                r = r_out if i % 2 == 0 else r_in
                theta = i * (math.pi / 5) - (math.pi / 2)
                x, y = r * math.cos(theta), r * math.sin(theta)
                if i == 0:
                    p.moveTo(x, y)
                else:
                    p.lineTo(x, y)
            p.close()
            c.drawPath(p, fill=1, stroke=1)
        c.restoreState()
    c.restoreState()

# =========================================================
# CACHES & WASHING
# =========================================================
MAX_UPLOAD_BYTES = 12 * 1024 * 1024  # 12MB pro Datei
MAX_TOTAL_UPLOAD_BYTES = 160 * 1024 * 1024  # 160MB total hard cap

def _get_lru(name: str, max_items: int) -> "OrderedDict":
    od = st.session_state.get(name)
    if not isinstance(od, OrderedDict):
        od = OrderedDict()
        st.session_state[name] = od
    st.session_state[f"{name}__max"] = max_items
    return od

def _lru_put(od: "OrderedDict", key, value, max_items: int):
    od[key] = value
    od.move_to_end(key)
    while len(od) > max_items:
        od.popitem(last=False)

def _read_upload_bytes(up) -> bytes:
    try:
        b = up.getvalue()
    except Exception:
        try:
            b = bytes(up.read())
        except Exception:
            b = b""
    if len(b) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Upload zu groß (max 12MB pro Bild): {getattr(up, 'name', 'Unbekannt')}")
    return b

def _wash_bytes(raw: bytes) -> bytes:
    if not raw:
        raise ValueError("empty upload")
    if hasattr(iw, "wash_image_bytes"):
        return bytes(iw.wash_image_bytes(raw))
    if hasattr(iw, "wash_bytes"):
        return bytes(iw.wash_bytes(raw))
    raise RuntimeError("image_wash logic missing")

def _wash_upload_to_bytes(up) -> bytes:
    raw = _read_upload_bytes(up)
    h = hashlib.sha256(raw).hexdigest()
    wc = _get_lru("wash_cache", MAX_WASH_CACHE)
    if h in wc:
        wc.move_to_end(h)
        return wc[h]
    w = _wash_bytes(raw)
    _lru_put(wc, h, w, MAX_WASH_CACHE)
    return w

def _sketch_compute(img_bytes: bytes, target_w: int, target_h: int) -> bytes:
    arr = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if arr is None:
        raise RuntimeError("OpenCV decode failed")

    h_arr, w_arr = arr.shape[:2]
    if (w_arr * h_arr) > 25_000_000:
        raise ValueError("Bildauflösung zu groß (max ~25MP).")

    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(255 - gray, (21, 21), 0)
    sketch = cv2.divide(gray, np.clip(255 - blurred, 1, 255), scale=256.0)
    norm = cv2.normalize(sketch, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    pil = Image.fromarray(norm).convert("L")
    sw, sh = pil.size
    s = min(sw, sh)
    pil = pil.crop(((sw - s) // 2, (sh - s) // 2, (sw + s) // 2, (sh + s) // 2)).resize((target_w, target_h), Image.LANCZOS)
    out = io.BytesIO()
    pil.point(lambda p: 255 if p > 200 else 0).convert("1").save(out, format="PNG", optimize=True)
    outv = out.getvalue()
    del arr, gray, blurred, sketch, norm, pil
    gc.collect()
    return outv

def _get_sketch_cached(img_bytes: bytes, target_w: int, target_h: int) -> bytes:
    cache = _get_lru("sketch_cache", MAX_SKETCH_CACHE)
    key = (hashlib.sha256(img_bytes).hexdigest(), int(target_w), int(target_h))
    if key in cache:
        cache.move_to_end(key)
        return cache[key]
    out = _sketch_compute(img_bytes, target_w, target_h)
    _lru_put(cache, key, out, MAX_SKETCH_CACHE)
    return out

# =========================================================
# OVERLAY (QUEST CARD) — Hour color = “time without clock”
# =========================================================
def _draw_quest_overlay(c, pb_w, pb_h, hour: int, mission: Mission):
    hh = 0.75 * inch
    x0 = 0.0
    w = pb_w
    ytb = pb_h - hh

    zone = _get_zone_for_hour(hour)
    z_rgb = _get_hour_color(hour)

    # Header color (unique per hour)
    c.saveState()
    c.setFillColor(colors.Color(z_rgb[0], z_rgb[1], z_rgb[2]))
    c.setStrokeColor(INK_BLACK)
    c.setLineWidth(1)
    c.rect(x0, ytb, w, hh, fill=1, stroke=1)

    c.setFillColor(colors.white if sum(z_rgb[:3]) < 1.5 else INK_BLACK)
    _set_font(c, True, 14)
    c.drawString(x0 + 0.18 * inch, ytb + hh - 0.50 * inch, f"{_fmt_hour(hour)}  {zone.icon}  {zone.name}")
    _set_font(c, False, 10)
    c.drawString(x0 + 0.18 * inch, ytb + 0.18 * inch, f"{zone.quest_type} • {zone.atmosphere}")

    # Card
    cy = 0.0
    ch = 2.85 * inch
    c.setFillColor(colors.white)
    c.setStrokeColor(INK_BLACK)
    c.rect(x0, cy, w, ch, fill=1, stroke=1)

    yc = cy + ch - 0.18 * inch
    c.setFillColor(INK_BLACK)

    _set_font(c, True, 13)
    c.drawString(x0 + 0.18 * inch, yc - 16, f"MISSION: {mission.title}")
    _set_font(c, True, 11)
    c.drawRightString(x0 + w - 0.18 * inch, yc - 16, f"+{int(mission.xp)} XP")

    # Bewegung
    _set_font(c, True, 10)
    c.drawString(x0 + 0.18 * inch, yc - 0.55 * inch, "BEWEGUNG:")
    _set_font(c, False, 10)
    mv = _fit_lines(_wrap_text_hard(mission.movement, FONTS["normal"], 10, w - 1.0 * inch), 2)
    yline = yc - 0.55 * inch
    for line in mv:
        c.drawString(x0 + 1.05 * inch, yline, line)
        yline -= 12.5

    # Suchen
    _set_font(c, True, 10)
    c.drawString(x0 + 0.18 * inch, yline - 0.18 * inch, "SUCHEN:")
    _set_font(c, False, 10)
    th = _fit_lines(_wrap_text_hard(mission.thinking, FONTS["normal"], 10, w - 1.0 * inch), 2)
    yline2 = yline - 0.18 * inch
    for line in th:
        c.drawString(x0 + 0.90 * inch, yline2, line)
        yline2 -= 12.5

    # Proof
    c.rect(x0 + 0.18 * inch, cy + 0.18 * inch, 0.20 * inch, 0.20 * inch, fill=0, stroke=1)
    _set_font(c, True, 10)
    c.drawString(x0 + 0.43 * inch, cy + 0.20 * inch, "PROOF:")
    _set_font(c, False, 10)
    pr = _fit_lines(_wrap_text_hard(mission.proof, FONTS["normal"], 10, w - 1.6 * inch), 1)[0]
    c.drawString(x0 + 1.03 * inch, cy + 0.20 * inch, pr)

    c.restoreState()

# =========================================================
# BUILDERS
# =========================================================
def build_interior(name, uploads, paper, build_nonce) -> bytes:
    if not uploads:
        raise ValueError("Keine Uploads vorhanden. Bitte lade Fotos hoch.")

    MAX_UPLOADS = 48
    if len(uploads) > MAX_UPLOADS:
        raise ValueError(f"Zu viele Uploads (max {MAX_UPLOADS}).")

    # total upload hard cap
    total_bytes = 0
    for up in uploads:
        try:
            total_bytes += len(up.getbuffer())
        except Exception:
            total_bytes += len(_read_upload_bytes(up))
        if total_bytes > MAX_TOTAL_UPLOAD_BYTES:
            raise ValueError("Uploads insgesamt zu groß (max 160MB). Bitte weniger/kleinere Bilder.")

    total_pages = KDP_PAGES_FIXED
    MISSION_PAGES = 24

    pb_w = TRIM + 2 * BLEED
    pb_h = TRIM + 2 * BLEED

    final = (list(uploads) * (MISSION_PAGES // len(uploads) + 1))[:MISSION_PAGES]

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(pb_w, pb_h))
    c.setTitle(f"{APP_TITLE} — Interior")
    c.setAuthor("Eddies World")
    c.setSubject(f"nonce={build_nonce}")

    schedule = build_book_schedule(_stable_seed(build_nonce), start_hour=6, count=MISSION_PAGES)

    # INTRO
    c.setFillColor(colors.white)
    c.rect(0, 0, pb_w, pb_h, fill=1, stroke=0)
    gen = _name_genitive(name)
    c.setFillColor(INK_BLACK)
    _set_font(c, True, 34)
    c.drawCentredString(pb_w / 2, pb_h - 2.00 * inch, f"{gen} Abenteuerbuch")
    _set_font(c, False, 14)
    c.drawCentredString(pb_w / 2, pb_h - 2.45 * inch, "Erstellt mit")
    _set_font(c, True, 18)
    c.drawCentredString(pb_w / 2, pb_h - 2.80 * inch, "E. P. E.")
    _set_font(c, False, 14)
    c.drawCentredString(pb_w / 2, pb_h - 3.10 * inch, "Eddie's Print Engine")
    _draw_eddie(c, pb_w / 2, pb_h / 2, 1.20 * inch, style="tongue")
    c.setFillColor(INK_GRAY_70)
    _set_font(c, False, 13)
    c.drawCentredString(pb_w / 2, 0.95 * inch, "24 Stunden • 24 Mini-Quests • Haken setzen")
    _imprint_nonce(c, build_nonce)
    c.showPage()

    # CONTENT
    for i, up in enumerate(final):
        target_w = int(pb_w * DPI / 72)
        target_h = int(pb_h * DPI / 72)

        img = _get_sketch_cached(_wash_upload_to_bytes(up), target_w, target_h)
        c.drawImage(ImageReader(io.BytesIO(img)), 0, 0, pb_w, pb_h)

        hour = (6 + i) % 24
        seed = int(_stable_seed(f"{build_nonce}|{i}|{hour}")) & 0xFFFFFFFF
        shapes = _generate_shapes(pb_w, pb_h, seed)
        _draw_shapes(c, shapes)

        tri = sum(1 for s in shapes if s.kind == "triangle")
        sq = sum(1 for s in shapes if s.kind == "square")
        st_ = sum(1 for s in shapes if s.kind == "star")
        total_shapes = len(shapes)

        q = schedule[hour]
        mission = Mission(
            title=q["title"],
            xp=q["xp"],
            movement=q["movement"],
            thinking=q["thinking"].format(tri=tri, sq=sq, st_=st_, total=total_shapes),
            proof=q["proof"],
        )

        _draw_quest_overlay(c, pb_w, pb_h, hour, mission)
        _imprint_nonce(c, build_nonce)
        c.showPage()
        gc.collect()

    # OUTRO (QR CTA) — ✅ Vector QR to /start/
    c.setFillColor(colors.white)
    c.rect(0, 0, pb_w, pb_h, fill=1, stroke=0)

    # Eddie top
    _draw_eddie(c, pb_w / 2, pb_h - 1.55 * inch, 0.80 * inch, style="tongue")

    c.setFillColor(INK_BLACK)
    _set_font(c, True, 26)
    c.drawCentredString(pb_w / 2, pb_h - 2.85 * inch, "Mach dein eigenes Abenteuer.")

    _set_font(c, False, 14)
    c.setFillColor(INK_GRAY_70)
    c.drawCentredString(pb_w / 2, pb_h - 3.45 * inch, "Dieses Buch ist eine feste Version.")
    c.drawCentredString(pb_w / 2, pb_h - 3.75 * inch, "Du kannst dein eigenes erstellen.")

    c.setFillColor(INK_BLACK)
    _set_font(c, True, 15)
    c.drawCentredString(pb_w / 2, pb_h - 4.55 * inch, "Mit deinem Namen.")
    c.drawCentredString(pb_w / 2, pb_h - 4.95 * inch, "Mit euren Fotos.")
    c.drawCentredString(pb_w / 2, pb_h - 5.35 * inch, "Sofort als PDF.")

    qr_url = "https://keschflow.github.io/start/"
    qr_code = qr.QrCodeWidget(qr_url)
    bounds = qr_code.getBounds()
    qr_w = bounds[2] - bounds[0]
    qr_h = bounds[3] - bounds[1]
    qr_size = 1.85 * inch
    scale = qr_size / max(qr_w, qr_h)
    d = Drawing(qr_size, qr_size, transform=[scale, 0, 0, scale, -bounds[0] * scale, -bounds[1] * scale])
    d.add(qr_code)

    renderPDF.draw(d, c, (pb_w - qr_size) / 2, pb_h - 7.65 * inch)

    c.setFillColor(INK_BLACK)
    _set_font(c, True, 12)
    c.drawCentredString(pb_w / 2, pb_h - 8.05 * inch, "keschflow.github.io/start")

    _set_font(c, False, 11)
    c.setFillColor(INK_GRAY_70)
    c.drawCentredString(pb_w / 2, pb_h - 8.45 * inch, "3 kostenlose Bücher testen.")

    _set_font(c, True, 12)
    c.setFillColor(INK_BLACK)
    c.drawCentredString(pb_w / 2, 1.05 * inch, "Kein Abo. Keine Anmeldung. Einfach testen.")

    _imprint_nonce(c, build_nonce)
    c.showPage()

    c.save()
    buf.seek(0)
    return buf.getvalue()

def build_cover(name, paper, uploads, build_nonce) -> bytes:
    # Minimal cover (keep stable). You can swap in your preflight cover later.
    sw = max(float(KDP_PAGES_FIXED) * PAPER_FACTORS.get(paper, 0.002252) * inch, 0.001 * inch)
    cw, ch = (2 * TRIM) + sw + (2 * BLEED), TRIM + (2 * BLEED)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(cw, ch))
    c.setTitle(f"{APP_TITLE} — Cover")
    c.setAuthor("Eddies World")
    c.setSubject(f"nonce={build_nonce}")

    c.setFillColor(colors.white)
    c.rect(0, 0, cw, ch, fill=1, stroke=0)

    # spine
    c.setFillColor(INK_BLACK)
    c.rect(BLEED + TRIM, BLEED, sw, TRIM, fill=1, stroke=0)

    # front
    fx = BLEED + TRIM + sw
    c.setFillColor(colors.white)
    c.rect(fx, BLEED, TRIM, TRIM, fill=1, stroke=0)

    gen = _name_genitive(name)
    c.setFillColor(INK_BLACK)
    _set_font(c, True, 30)
    c.drawCentredString(fx + TRIM / 2, BLEED + TRIM * 0.86, f"{gen}")
    _set_font(c, True, 24)
    c.drawCentredString(fx + TRIM / 2, BLEED + TRIM * 0.80, "ABENTEUERBUCH")
    _set_font(c, False, 11)
    c.setFillColor(INK_GRAY_70)
    c.drawCentredString(fx + TRIM / 2, BLEED + TRIM * 0.75, "Erstellt mit E. P. E. — Eddie's Print Engine")
    _draw_eddie(c, fx + TRIM / 2, BLEED + TRIM * 0.58, TRIM * 0.14, style="tongue")

    _imprint_nonce(c, build_nonce)
    c.save()
    buf.seek(0)
    return buf.getvalue()

# =========================================================
# UI
# =========================================================
st.set_page_config(page_title=APP_TITLE, layout="centered", page_icon=APP_ICON)

st.markdown(f"<h1 style='text-align:center; margin-bottom: 0;'>{APP_TITLE}</h1>", unsafe_allow_html=True)
st.caption(f"Build: {BUILD_TAG}")

if is_supporter:
    st.success("💖 Unterstützer-Modus aktiv: Unlimitierte Builds freigeschaltet.")
elif access_mode == "Community":
    st.info(f"🏫 Community-Pass aktiv: {builds_left} Builds in den letzten 24h verfügbar.")
elif access_mode == "Dev Mode":
    st.info("🧪 Dev Mode aktiv: Unlimitierter Zugriff (keine Stripe Secrets).")
else:
    st.info(f"🔓 Open Access: ({builds_left} kostenlose Builds in den letzten 24h übrig)")

if access_mode == "Free":
    with st.expander("🏫 Hast du einen Community-Pass? (Kitas, Schulen, Therapeuten)"):
        c_code = st.text_input("Code eingeben:", key="c_code_input")
        if st.button("Passwort aktivieren"):
            if c_code in COMMUNITY_TOKENS:
                st.session_state["community_pass"] = c_code
                st.success("Passwort akzeptiert! Seite wird neu geladen...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Ungültiger Code.")

if qd is None:
    st.warning("quest_data.py fehlt – Engine läuft trotzdem (Fallback-Welt aktiv).")
    if "_QD_IMPORT_ERROR" in globals() and _QD_IMPORT_ERROR:
        st.code(_QD_IMPORT_ERROR, language="text")

st.session_state.setdefault("assets", None)
_get_lru("sketch_cache", MAX_SKETCH_CACHE)
_get_lru("wash_cache", MAX_WASH_CACHE)

with st.container(border=True):
    c1, c2 = st.columns(2)
    name = c1.text_input("Name des Kindes", "Eddie")

    c2.markdown("**Seitenanzahl**")
    c2.info("📘 Fix 26 Seiten (KDP-Ready)")
    paper = c2.selectbox("Papier", list(PAPER_FACTORS.keys()), 0)

    st.divider()
    st.info("💡 Tipp: Es müssen keine Personen zu sehen sein! Haustiere, Zimmer, Spielzeug oder Garten funktionieren super.")
    uploads = st.file_uploader("Fotos hochladen (10-24 empfohlen)", accept_multiple_files=True, type=["jpg", "jpeg", "png", "webp"])

if uploads:
    st.success(f"✅ {len(uploads)} Fotos bereit für die Engine.")

if not can_build_limit:
    st.error("🛑 Fair-Use Limit erreicht (24h).")
    st.markdown("Werde Unterstützer für unlimitierte Builds.")
    st.link_button("💖 Unterstützer werden (Unlimitiert)", PAYMENT_LINK, type="primary")
    st.stop()

if st.button("🚀 QUESTBUCH GENERIEREN", disabled=not (uploads and name), type="primary"):
    nonce = _new_build_nonce()

    with st.spinner("Engine läuft..."):
        try:
            int_pdf = build_interior(name=name, uploads=uploads, paper=str(paper), build_nonce=nonce)
            cov_pdf = build_cover(name=name, paper=str(paper), uploads=uploads, build_nonce=nonce)
            st.session_state.assets = {"int": int_pdf, "cov": cov_pdf, "name": name, "nonce": nonce}
            _log_build(client_ip)
            st.success(f"🎉 Assets bereit! (Noch {max(0, builds_left - 1)} kostenlose Builds in den letzten 24h)")
        except Exception as e:
            st.error(f"⚠️ Engine gestolpert: `{str(e)}`")

if st.session_state.assets:
    a = st.session_state.assets
    st.markdown("### 📥 Deine druckfertigen PDFs")
    col1, col2 = st.columns(2)
    col1.download_button("📘 Innenseiten (PDF)", a["int"], f"Int_{a['name']}.pdf", use_container_width=True)
    col2.download_button("🎨 Cover (PDF)", a["cov"], f"Cov_{a['name']}.pdf", use_container_width=True)
    st.caption(f"Security Nonce: `{a.get('nonce','')}`")

st.markdown("<div style='text-align:center; color:grey; margin-top: 50px;'>Eddies World © 2026 • Ein Projekt für jedes Kind.</div>", unsafe_allow_html=True)
