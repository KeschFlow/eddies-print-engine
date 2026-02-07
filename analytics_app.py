import streamlit as st
import csv
import os
from datetime import datetime, timedelta
import random

st.set_page_config(page_title="Eddie’s Welt – Analytics", layout="wide")
st.title("📊 Eddie’s Welt – Analytics Dashboard")

# =========================================================
# SETTINGS
# =========================================================
DEFAULT_LOG_PATH = "data/usage_log.csv"

with st.sidebar:
    st.header("Einstellungen")
    log_path = st.text_input("CSV Log Pfad", DEFAULT_LOG_PATH)
    simulate = st.toggle("🧪 Simulationsmodus (Demo-Daten)", value=True)
    days = st.slider("Zeitraum (Tage)", 7, 90, 30)
    st.divider()
    st.caption("Wenn du echte Daten loggen willst: app.py schreibt pro Export 1 Zeile in diese CSV.")

# =========================================================
# DATA
# =========================================================
FIELDS = ["ts", "kdp_mode", "dpi", "pdf_mb", "jpeg_quality", "status"]  # status: ok|fail

def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)

def _read_csv(path: str):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows

def _simulate_rows(n_days: int):
    now = datetime.utcnow()
    rows = []
    for d in range(n_days):
        day = now - timedelta(days=(n_days - 1 - d))
        exports = random.randint(0, 12)
        for _ in range(exports):
            kdp = random.random() < 0.55
            dpi = random.choice([180, 240, 300]) if kdp else 0
            pdf = random.uniform(8, 60) if not kdp else random.uniform(25, 120)
            q = random.choice([60, 65, 70, 75, 80, 85])
            status = "ok" if random.random() < 0.92 else "fail"
            ts = (day + timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M:%S")
            rows.append({
                "ts": ts,
                "kdp_mode": "1" if kdp else "0",
                "dpi": str(dpi),
                "pdf_mb": f"{pdf:.1f}",
                "jpeg_quality": str(q),
                "status": status,
            })
    return rows

def _filter_days(rows, n_days: int):
    if not rows:
        return rows
    cutoff = datetime.utcnow() - timedelta(days=n_days)
    out = []
    for r in rows:
        try:
            t = datetime.strptime(r["ts"], "%Y-%m-%d %H:%M:%S")
            if t >= cutoff:
                out.append(r)
        except:
            continue
    return out

rows = _simulate_rows(days) if simulate else _read_csv(log_path)
rows = _filter_days(rows, days)

# =========================================================
# METRICS
# =========================================================
def _to_float(x, default=0.0):
    try: return float(x)
    except: return default

def _to_int(x, default=0):
    try: return int(float(x))
    except: return default

total = len(rows)
ok = sum(1 for r in rows if r.get("status") == "ok")
fail = total - ok
kdp = sum(1 for r in rows if r.get("kdp_mode") == "1")
a4 = total - kdp
avg_pdf = sum(_to_float(r.get("pdf_mb")) for r in rows) / max(1, total)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Exports (gesamt)", total)
col2.metric("Erfolgreich", ok)
col3.metric("Fehlgeschlagen", fail)
col4.metric("KDP / A4", f"{kdp} / {a4}")
col5.metric("Ø PDF (MB)", f"{avg_pdf:.1f}")

st.divider()

# =========================================================
# CHARTS (Streamlit-native)
# =========================================================
# Daily aggregation
daily = {}
for r in rows:
    try:
        day = r["ts"][:10]
        daily.setdefault(day, {"ok": 0, "fail": 0, "kdp": 0, "a4": 0, "pdf_sum": 0.0, "n": 0})
        bucket = daily[day]
        bucket["n"] += 1
        if r.get("status") == "ok":
            bucket["ok"] += 1
        else:
            bucket["fail"] += 1
        if r.get("kdp_mode") == "1":
            bucket["kdp"] += 1
        else:
            bucket["a4"] += 1
        bucket["pdf_sum"] += _to_float(r.get("pdf_mb"))
    except:
        pass

days_sorted = sorted(daily.keys())
series_exports = [daily[d]["n"] for d in days_sorted]
series_ok = [daily[d]["ok"] for d in days_sorted]
series_fail = [daily[d]["fail"] for d in days_sorted]
series_avg_pdf = [daily[d]["pdf_sum"] / max(1, daily[d]["n"]) for d in days_sorted]

c1, c2 = st.columns([2, 2])

with c1:
    st.subheader("📈 Exports pro Tag")
    st.line_chart({"exports": series_exports, "ok": series_ok, "fail": series_fail}, x=days_sorted)

with c2:
    st.subheader("📦 Ø PDF Größe pro Tag (MB)")
    st.line_chart({"avg_pdf_mb": series_avg_pdf}, x=days_sorted)

st.divider()

st.subheader("🧾 Raw Events (letzte 200)")
st.dataframe(rows[-200:], use_container_width=True)

if not simulate:
    if not os.path.exists(log_path):
        st.warning("Noch keine CSV gefunden. Lege sie an oder aktiviere Simulationsmodus.")
        _ensure_dir(log_path)
        # optional: create header file
        with open(log_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
        st.info("CSV-Header wurde angelegt.")

