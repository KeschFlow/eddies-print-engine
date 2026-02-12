# kern/subject_data.py
# Berufssprachliche Vokabeln – optimiert für DaZ / Integrationskurse
from __future__ import annotations

from typing import Dict, List


# =========================================================
# 1) Fachbereiche + Vokabeln
# =========================================================
SUBJECTS: Dict[str, List[dict]] = {
    "Schneidern": [
        {"wort": "die Nadel",           "satz": "Ich brauche eine neue Nadel zum Nähen."},
        {"wort": "der Stoff",           "satz": "Der Stoff ist weich und blau."},
        {"wort": "die Schere",          "satz": "Ich schneide den Stoff mit der Schere."},
        {"wort": "das Maßband",         "satz": "Ich messe die Länge mit dem Maßband."},
        {"wort": "der Reißverschluss",  "satz": "Der Reißverschluss ist kaputt."},
        {"wort": "der Faden",           "satz": "Ich ziehe den Faden durch die Nadel."},
    ],
    "Pflege": [
        {"wort": "der Verband",         "satz": "Ich wechsle den Verband beim Patienten."},
        {"wort": "der Blutdruck",       "satz": "Wir messen jeden Morgen den Blutdruck."},
        {"wort": "die Pflegekraft",     "satz": "Die Pflegekraft hilft beim Aufstehen."},
        {"wort": "das Fieber",          "satz": "Das Fieber ist auf 38,5 Grad gestiegen."},
        {"wort": "die Spritze",         "satz": "Ich bereite die Spritze für die Impfung vor."},
        {"wort": "der Rollstuhl",       "satz": "Ich schiebe den Rollstuhl zum Aufzug."},
    ],
    "Gastronomie": [
        {"wort": "die Speisekarte",     "satz": "Die Speisekarte liegt auf dem Tisch."},
        {"wort": "der Kellner",         "satz": "Der Kellner nimmt die Bestellung auf."},
        {"wort": "das Trinkgeld",       "satz": "Vielen Dank für das Trinkgeld!"},
        {"wort": "die Rechnung",        "satz": "Hier ist Ihre Rechnung, bitte sehr."},
        {"wort": "der Teller",          "satz": "Ich stelle den Teller vor den Gast."},
        {"wort": "die Küche",           "satz": "In der Küche arbeiten zwei Köche."},
    ],
    "Büro & Verwaltung": [
        {"wort": "der Computer",        "satz": "Ich arbeite am Computer im Büro."},
        {"wort": "die Akte",            "satz": "Bitte bringen Sie die Akte mit."},
        {"wort": "der Termin",          "satz": "Der Termin ist um 14 Uhr."},
        {"wort": "die E-Mail",          "satz": "Ich schreibe eine E-Mail an den Chef."},
    ],
}


# =========================================================
# 2) Icon-Slugs (müssen zu kern/pdf_engine.py passen!)
# =========================================================
# Gültige Keys in deiner ICON_DRAWERS Registry (pdf_engine.py):
# hammer, wrench, gear, medical, briefcase, teacher, gastro, computer,
# scissors, syringe, envelope, calendar, wheelchair, tray

AUTO_ICON: Dict[str, str] = {
    # ---- Schneidern
    "schneidern": "scissors",
    "schere": "scissors",
    "nadel": "scissors",         # fallback bis needle-icon existiert
    "stoff": "scissors",         # fallback bis fabric-icon existiert
    "maßband": "scissors",
    "reißverschluss": "scissors",
    "faden": "scissors",

    # ---- Pflege
    "pflege": "medical",
    "verband": "medical",
    "blutdruck": "medical",
    "pflegekraft": "medical",
    "fieber": "medical",
    "spritze": "syringe",
    "rollstuhl": "wheelchair",

    # ---- Gastronomie
    "gastronomie": "tray",
    "kellner": "tray",
    "speisekarte": "tray",
    "trinkgeld": "tray",
    "rechnung": "tray",
    "teller": "tray",
    "küche": "tray",

    # ---- Büro
    "büro": "briefcase",         # EINDEUTIG: nicht doppelt
    "verwaltung": "briefcase",
    "akte": "briefcase",
    "computer": "computer",
    "termin": "calendar",
    "e-mail": "envelope",
    "email": "envelope",

    # ---- Generische / Industrie
    "metall": "hammer",
    "werkzeug": "hammer",
    "werkstatt": "gear",

    # ---- Schule / Bildung (falls später genutzt)
    "lehrer": "teacher",
    "schule": "teacher",
}


# =========================================================
# 3) Helper: Icon-Slug aus Fach oder Wort ableiten
# =========================================================
def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    # sanftes Normalisieren (Umlaute bleiben, weil Keys auch Umlaute enthalten können)
    return s


def get_icon_slug(subject: str, *, wort: str | None = None) -> str:
    """
    Priorität:
      1) Wort (wenn gegeben) -> AUTO_ICON
      2) Fachbereich -> AUTO_ICON
      3) Fallback -> "teacher"
    """
    if wort:
        k = _norm(wort)
        if k in AUTO_ICON:
            return AUTO_ICON[k]

    s = _norm(subject)
    if s in AUTO_ICON:
        return AUTO_ICON[s]

    return "teacher"