# app_trainer.py — Eddie Trainer V2 (Platinum) • FINAL UI (Export-Matrix)
# Features:
# - Fach auswählen (SUBJECTS) ODER eigene Vokabeln tippen
# - Optional: Bilder hochladen (zyklisch verteilt, RAM-only bytes)
# - Export-Matrix per Klick:
#     1) KDP Buch (Square 8.5x8.5 + Bleed, Preflight min. 24 Seiten)
#     2) A4 Arbeitsblatt (große Schreibflächen)
#     3) QR Lernkarten (6er Grid, Vorder/Rückseite, Offline-QR)
#
# Voraussetzung:
# - kern/export_orchestrator.py delegiert nach:
#     - kern/exports/trainer_a4.py
#     - kern/exports/trainer_cards.py
#     - kern/exports/trainer_kdp.py
#
# Offline-First: Keine APIs. Assets werden als bytes an den Export übergeben.

from __future__ import annotations

import streamlit as st
from typing import List, Tuple

from kern.export_orchestrator import run_export

# Optional: subject_data (falls vorhanden)
try:
    from kern.subject_data import SUBJECTS, AUTO_ICON
except Exception:
    SUBJECTS = {}
    AUTO_ICON = {}


# -----------------------------
# Parsing / Datenaufbereitung
# -----------------------------
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


# ---------------- UI ----------------
st.set_page_config(page_title="Eddie Trainer V2", layout="centered")
st.title("🗣️ Eddie Trainer V2 – Fachsprache als Druckprodukt (A4 / KDP / QR)")

with st.sidebar:
    st.header("⚙️ Export-Konfiguration")

    export_mode = st.selectbox(
        "Format wählen",
        ["KDP Buch", "A4 Arbeitsblatt", "QR Lernkarten"],
        help="Wähle das Format passend zu deiner Zielgruppe.",
    )

    watermark = st.toggle("Branding: lila Zunge (Wasserzeichen)", value=True)

    # Modus-spezifische Optionen
    if export_mode == "KDP Buch":
        st.caption("KDP: Square 8.5×8.5\" + Bleed • Preflight min. 24 Seiten")
        min_pages = st.slider("KDP Mindestseiten", 24, 120, 24, 2)
        writing_lines = st.slider("Schreiblinien (Niveau)", 2, 10, 5, 1)
        include_quiz = st.toggle("Quiz (später optional)", value=False, disabled=True)
    elif export_mode == "A4 Arbeitsblatt":
        st.caption("A4: große Schreibflächen • druckerfreundlich")
        lines_on = st.toggle("Schreiblinien anzeigen", value=True)
        writing_lines = st.slider("Schreiblinien pro Seite", 2, 10, 5, 1)
        min_pages = None
        include_quiz = False
    else:  # QR Lernkarten
        st.caption("QR Lernkarten: 6er Grid • Vorder/Rückseite • Offline-QR")
        lines_on = False
        writing_lines = 5
        min_pages = None
        include_quiz = False

st.subheader("1) Fach wählen oder eigene Vokabeln nutzen")

mode = st.radio(
    "Quelle der Vokabeln",
    ["Fach-Modul (vorbelegt)", "Eigene Eingabe (Copy/Paste)"],
    horizontal=True,
)

subject = "Eigenes Fach"
default_text = "die Nadel;needle\nStoff;fabric\nSchere;scissors"

if mode == "Fach-Modul (vorbelegt)" and SUBJECTS:
    subject = st.selectbox("Fachgebiet", list(SUBJECTS.keys()), index=0)
    preset = SUBJECTS.get(subject, [])
    lines: List[str] = []
    for it in preset:
        if isinstance(it, dict):
            lines.append(str(it.get("wort", "")).strip())
        elif isinstance(it, (list, tuple)) and len(it) >= 1:
            lines.append(str(it[0]).strip())
    default_text = "\n".join([ln for ln in lines if ln]) or default_text
else:
    subject = st.text_input("Fach / Thema (frei)", value="Schneidern")

raw_text = st.text_area(
    "Vokabeln (pro Zeile: deutsch;übersetzung ODER nur deutsch)",
    value=default_text,
    height=220,
)

st.subheader("2) Optional: Bilder hochladen (sonst Icon-Fallback in Exportern)")
uploads = st.file_uploader(
    "Bilder (werden zyklisch verteilt, RAM-only)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

vocab_pairs = parse_vocab_lines(raw_text)

st.caption(
    "Hinweis: Bilder werden als Bytes im RAM an die Export-Module übergeben. "
    "Keine Cloud, keine APIs. Wenn keine Bilder da sind, nutzen die Exporte Icon-Fallback."
)

# -----------------------------
# Export Action
# -----------------------------
disabled = not bool(vocab_pairs)

if st.button("Export erstellen", type="primary", disabled=disabled):
    try:
        data = {
            "module": "trainer_v2",
            "subject": subject,
            "vocab": [{"word": w, "translation": t} for (w, t) in vocab_pairs],
            "assets": {
                "images": [up.getvalue() for up in (uploads or [])],
            },
            "options": {
                "writing_lines_per_page": int(writing_lines),
                "include_quiz": bool(include_quiz),
            },
        }

        # kwargs je nach Modus
        kwargs = {
            "title": "Eddie Trainer V2",
            "subtitle": f"Fach: {subject}",
            "watermark": bool(watermark),
        }

        if export_mode == "A4 Arbeitsblatt":
            kwargs["lines"] = bool(lines_on)

        if export_mode == "KDP Buch":
            kwargs["min_pages"] = int(min_pages)

        pdf_bytes = run_export(export_mode, data, **kwargs)

        st.success("PDF erstellt ✅")

        filename = f"eddie_trainer_v2_{export_mode.lower().replace(' ', '_')}_{subject.lower().replace(' ', '_')}.pdf"
        st.download_button(
            "PDF herunterladen",
            pdf_bytes,
            file_name=filename,
            mime="application/pdf",
        )

    except Exception as e:
        st.error(f"Fehler beim Erstellen: {e}")
