import streamlit as st
import os
import csv
import time
import random
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict

# =========================================================
# STREAMLIT CONFIG (MUSS ALS ERSTES KOMMEN)
# =========================================================
st.set_page_config(page_title="Eddie's Welt – Analytics", layout="wide")

# =========================================================
# SETTINGS
# =========================================================
DEFAULT_CSV_PATH = "data/usage.csv"

# CSV schema (recommended)
# ts_iso, event, kdp_mode, dpi, pdf_mb, jpeg_quality, num_uploads, ok, error_msg
SCHEMA = [
    "ts_iso",
    "event",
    "kdp_mode",
    "dpi",
    "pdf_mb",
    "jpeg_quality",
    "num_uploads",
    "ok",
    "error_msg",
]

# =========================================================
# HELPERS
# =========================================================
def _now_utc():
    return datetime.now(timezone.utc)

def _parse_bool(x: str) -> bool:
    return str(x).strip().lower() in ("1", "true", "yes", "y", "on")

def _parse_int(x: str, default=0) -> int:
    try:
        return int(float(str(x).strip()))
    except:
        return default

def _parse_float(x: str, default=0.0) -> float:
    try:
        return float(str(x).strip())
    except:
        return default

def _parse_dt(ts_iso: str):
    try:
        # accepts ISO like: 2026-02-08T12:34:56Z or +00:00
        s = ts_iso.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except:
        return None

def _safe_get(row: dict, key: str, default=""):
    v = row.get(key, default)
    return "" if v is None else v

def load_events_from_csv(csv_path: str):
    if not os.path.exists(csv_path):
        return []

    events = []
    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                ts = _parse_dt(_safe_get(r, "ts_iso", ""))
                if ts is None:
                    continue
                ev = {
                    "ts": ts,
                    "event": _safe_get(r, "event", "").strip() or "generate",
                    "kdp_mode": _parse_bool(_safe_get(r, "kdp_mode", "false")),
                    "dpi": _parse_int(_safe_get(r, "dpi", "0"), 0),
                    "pdf_mb": _parse_float(_safe_get(r, "pdf_mb", "0"), 0.0),
                    "jpeg_quality": _parse_int(_safe_get(r, "jpeg_quality", "0"), 0),
                    "num_uploads": _parse_int(_safe_get(r, "num_uploads", "0"), 0),
                    "ok": _parse_bool(_safe_get(r, "ok", "true")),
                    "error_msg": _safe_get(r, "error_msg", "").strip(),
                }
                events.append(ev)
    except Exception:
        # if CSV is malformed, don't kill the dashboard
        return []

    return events

def simulate_events(days_back: int = 14, n: int = 250, seed: int = 1337):
    random.seed(seed)
    base = _now_utc() - timedelta(days=days_back)
    events = []
    for _ in range(n):
        ts = base + timedelta(seconds=random.randint(0, days_back * 24 * 3600))
        kdp = random.random() < 0.55
        dpi = random.choice([180, 240, 300]) if kdp else 0
        num_uploads = random.randint(6, 24)
        ok = random.random() > (0.08 if kdp else 0.04)
        q = random.choice([60, 65, 70, 75, 80, 85]) if kdp else 85

        # rough pdf size model
        if kdp:
            pdf_mb = max(
                8.0,
                min(
                    180.0,
                    (num_uploads * 2.5)
                    + (5 if dpi == 300 else 0)
                    + random.uniform(-8, 12),
                ),
            )
        else:
            pdf_mb = max(4.0, min(80.0, (num_uploads * 1.4) + random.uniform(-5, 8)))

        err = "" if ok else random.choice(
            [
                "Upload- oder Dekodier-Fehler",
                "OpenCV decode failed",
                "PIL EXIF read error",
                "Memory error during export",
            ]
        )
        events.append(
            {
                "ts": ts,
                "event": "generate",
                "kdp_mode": kdp,
                "dpi": dpi,
                "pdf_mb": float(pdf_mb),
                "jpeg_quality": int(q),
                "num_uploads": int(num_uploads),
                "ok": bool(ok),
                "error_msg": err,
            }
        )
    events.sort(key=lambda x: x["ts"])
    return events

def filter_events(events, since_dt, kdp_filter: str):
    out = []
    for e in events:
        if e["ts"] < since_dt:
            continue
        if kdp_filter == "KDP":
            if not e["kdp_mode"]:
                continue
        elif kdp_filter == "A4":
            if e["kdp_mode"]:
                continue
        out.append(e)
    return out

def group_by_day(events):
    # returns list of (day_str, count_total, count_ok, count_fail, avg_mb, avg_q)
    buckets = defaultdict(list)
    for e in events:
        day = e["ts"].astimezone(timezone.utc).strftime("%Y-%m-%d")
        buckets[day].append(e)

    rows = []
    for day in sorted(buckets.keys()):
        xs = buckets[day]
        total = len(xs)
        ok = sum(1 for z in xs if z["ok"])
        fail = total - ok
        avg_mb = sum(z["pdf_mb"] for z in xs) / total if total else 0.0
        avg_q = sum(z["jpeg_quality"] for z in xs) / total if total else 0.0
        rows.append((day, total, ok, fail, avg_mb, avg_q))
    return rows

def _pct(a, b):
    return (100.0 * a / b) if b else 0.0

# =========================================================
# UI
# =========================================================
st.title("📊 Eddie’s Welt – Analytics")

with st.sidebar:
    st.header("Datenquelle")
    csv_path = st.text_input("CSV Pfad", value=DEFAULT_CSV_PATH)
    auto_sim = st.toggle("Auto-Simulation wenn CSV fehlt", value=True)
    force_sim = st.toggle("Simulation erzwingen", value=False)
    st.divider()

    st.header("Filter")
    days = st.slider("Zeitraum (Tage)", min_value=1, max_value=90, value=14)
    kdp_filter = st.selectbox("Modus", options=["Alle", "KDP", "A4"], index=0)
    st.divider()

    st.header("Simulation")
    sim_n = st.slider("Sim-Events", min_value=50, max_value=2000, value=350, step=50)
    sim_seed = st.number_input("Sim-Seed", min_value=1, max_value=999999, value=1337, step=1)

# Load
events = []
source_label = ""

if force_sim:
    events = simulate_events(days_back=max(7, days), n=int(sim_n), seed=int(sim_seed))
    source_label = "SIMULATION (forced)"
else:
    real = load_events_from_csv(csv_path)
    if real:
        events = real
        source_label = f"CSV: {csv_path}"
    else:
        if auto_sim:
            events = simulate_events(days_back=max(7, days), n=int(sim_n), seed=int(sim_seed))
            source_label = "SIMULATION (CSV missing/empty)"
        else:
            events = []
            source_label = "NO DATA (CSV missing/empty)"

st.caption(f"Quelle: **{source_label}** | Events: **{len(events)}**")

# Time filter
since_dt = _now_utc() - timedelta(days=int(days))
events_f = filter_events(events, since_dt=since_dt, kdp_filter=kdp_filter)

# KPIs
total = len(events_f)
ok = sum(1 for e in events_f if e["ok"])
fail = total - ok
kdp_count = sum(1 for e in events_f if e["kdp_mode"])
a4_count = total - kdp_count

avg_mb = sum(e["pdf_mb"] for e in events_f) / total if total else 0.0
avg_q = sum(e["jpeg_quality"] for e in events_f) / total if total else 0.0
avg_uploads = sum(e["num_uploads"] for e in events_f) / total if total else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Generierungen", f"{total}")
c2.metric("Erfolgsrate", f"{_pct(ok, total):.1f}%", f"{fail} Fehler")
c3.metric("Ø PDF Größe", f"{avg_mb:.1f} MB")
c4.metric("Ø JPEG Qualität", f"{avg_q:.0f}%")

c5, c6, c7 = st.columns(3)
c5.metric("KDP", f"{kdp_count}", f"{_pct(kdp_count, total):.1f}%")
c6.metric("A4", f"{a4_count}", f"{_pct(a4_count, total):.1f}%")
c7.metric("Ø Uploads", f"{avg_uploads:.1f}", "max 24")

st.divider()

# Daily series
rows = group_by_day(events_f)
if not rows:
    st.warning("Keine Daten im gewählten Zeitraum / Filter. (Oder CSV leer.)")
else:
    # Streamlit charts accept dicts/lists
    days_x = [r[0] for r in rows]
    total_y = [r[1] for r in rows]
    ok_y = [r[2] for r in rows]
    fail_y = [r[3] for r in rows]
    mb_y = [round(r[4], 2) for r in rows]
    q_y = [round(r[5], 0) for r in rows]

    st.subheader("📈 Trend pro Tag")

    cc1, cc2 = st.columns(2)
    with cc1:
        st.caption("Generierungen (Total / OK / Fail)")
        st.line_chart(
            {
                "total": total_y,
                "ok": ok_y,
                "fail": fail_y,
            }
        )
    with cc2:
        st.caption("Ø PDF Größe (MB) & Ø Qualität (%)")
        st.line_chart(
            {
                "pdf_mb": mb_y,
                "jpeg_quality": q_y,
            }
        )

    st.divider()

    # Breakdowns
    st.subheader("🧠 Breakdown")

    left, right = st.columns(2)

    with left:
        st.caption("DPI (nur KDP)")
        dpi_counter = Counter(e["dpi"] for e in events_f if e["kdp_mode"])
        if dpi_counter:
            st.bar_chart({str(k): v for k, v in sorted(dpi_counter.items())})
        else:
            st.info("Keine KDP-Daten im Filter.")

        st.caption("PDF Größen-Buckets (MB)")
        buckets = Counter()
        for e in events_f:
            mb = e["pdf_mb"]
            if mb < 40: b = "<40"
            elif mb < 80: b = "40-79"
            elif mb < 120: b = "80-119"
            elif mb < 150: b = "120-149"
            else: b = "150+"
            buckets[b] += 1
        st.bar_chart(buckets)

    with right:
        st.caption("Top Fehlerursachen")
        errs = Counter(e["error_msg"] for e in events_f if not e["ok"] and e["error_msg"])
        if errs:
            # show top 10
            for msg, cnt in errs.most_common(10):
                st.write(f"- **{cnt}×** {msg}")
        else:
            st.info("Keine Fehler im Filter (oder keine error_msg in CSV).")

        st.caption("Letzte Events (10)")
        last = sorted(events_f, key=lambda x: x["ts"], reverse=True)[:10]
        for e in last:
            ts = e["ts"].astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            mode = "KDP" if e["kdp_mode"] else "A4"
            status = "OK" if e["ok"] else "FAIL"
            st.write(
                f"- `{ts}` | **{status}** | {mode} | dpi={e['dpi']} | {e['pdf_mb']:.1f}MB | q={e['jpeg_quality']} | uploads={e['num_uploads']}"
            )

st.divider()

# CSV schema helper
with st.expander("🧾 CSV Schema (für echten Betrieb)"):
    st.write("Lege eine Datei an: `data/usage.csv` (wird später von app.py befüllt).")
    st.code(",".join(SCHEMA), language="text")
    st.write("Beispielzeile:")
    st.code(
        "2026-02-08T12:34:56+00:00,generate,true,240,78.2,85,24,true,",
        language="text",
    )
