# =========================================================
# quest_data.py — Eddie’s World (World-Building Layer)
# Compatible with: app.py v5.10.x (dynamic quest bank)
# =========================================================
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple

@dataclass(frozen=True)
class Zone:
    name: str
    icon: str
    quest_type: str
    atmosphere: str = ""

EDDIE_PURPLE: Tuple[float, float, float] = (0.486, 0.227, 0.929)  # ~#7c3aed

def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else float(x)

def _mix(a: Tuple[float, float, float], b: Tuple[float, float, float], t: float) -> Tuple[float, float, float]:
    t = _clamp01(t)
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)

def _brighten(rgb: Tuple[float, float, float], amt: float) -> Tuple[float, float, float]:
    return _mix(rgb, (1.0, 1.0, 1.0), _clamp01(amt))

def _darken(rgb: Tuple[float, float, float], amt: float) -> Tuple[float, float, float]:
    return _mix(rgb, (0.0, 0.0, 0.0), _clamp01(amt))

ZONES: Dict[int, Zone] = {
    0:  Zone("Mondwache", "🌙", "Ruhe-Quest", "leise"),
    1:  Zone("Sternenpfad", "✨", "Traum-Quest", "sanft"),
    2:  Zone("Nebelinsel", "🌫️", "Stille-Quest", "ruhig"),
    3:  Zone("Schlaf-Ninja", "🥷", "Mini-Quest", "ganz leise"),
    4:  Zone("Dämmerraum", "🌌", "Reset-Quest", "locker"),
    5:  Zone("Frühfunken", "🔥", "Warm-up", "wach werden"),
    6:  Zone("Morgen-Start", "🌤️", "Warm-up", "ruhig"),
    7:  Zone("Kraft-Küche", "🍳", "Action", "frisch"),
    8:  Zone("Fokus-Feld", "🎯", "Mission", "klar"),
    9:  Zone("Sonnen-Sprung", "☀️", "Action", "energetisch"),
    10: Zone("Abenteuer-Check", "🧭", "Mission", "bereit"),
    11: Zone("Mittags-Mission", "🌞", "Action", "wach"),
    12: Zone("Turbo-Wald", "🌲", "Abenteuer", "mutig"),
    13: Zone("Formenfestung", "🏰", "Quest", "fokussiert"),
    14: Zone("Sprint-Strand", "🏖️", "Action", "schnell"),
    15: Zone("Power-Plateau", "⛰️", "Mission", "stark"),
    16: Zone("Nachmittags-Boost", "🟣", "Abenteuer", "spielerisch"),
    17: Zone("Eddie-Arena", "🐶", "Quest", "frech"),
    18: Zone("Dämmer-Deck", "🌆", "Mission", "warm"),
    19: Zone("Kuschel-Kommando", "🧸", "Mini-Quest", "weich"),
    20: Zone("Abend-Fokus", "🕯️", "Reset-Quest", "ruhig"),
    21: Zone("Abend-Ruhe", "🌙", "Runterfahren", "sanft"),
    22: Zone("Traum-Scanner", "🔭", "Stille-Quest", "leicht"),
    23: Zone("Nacht-Auge", "👁️", "Mini-Quest", "ganz ruhig"),
}

def get_hour_color(hour: int) -> Tuple[float, float, float]:
    h = int(hour) % 24
    night = _darken(EDDIE_PURPLE, 0.45)
    dawn = _mix((0.95, 0.60, 0.30), EDDIE_PURPLE, 0.55)
    day = _brighten(EDDIE_PURPLE, 0.18)
    sunset = _mix((0.95, 0.35, 0.25), EDDIE_PURPLE, 0.65)

    if 0 <= h <= 4:
        t = h / 4.0
        return _mix(_darken(night, 0.15), night, t)
    if h == 5:
        return _mix(night, dawn, 0.60)
    if 6 <= h <= 10:
        t = (h - 6) / 4.0
        return _mix(dawn, day, t)
    if 11 <= h <= 15:
        t = (h - 11) / 4.0
        return _mix(day, _brighten(day, 0.10), t)
    if 16 <= h <= 18:
        t = (h - 16) / 2.0
        return _mix(day, sunset, t)
    if 19 <= h <= 21:
        t = (h - 19) / 2.0
        return _mix(sunset, night, t)
    t = (h - 22) / 1.0 if h >= 22 else 0.0
    return _mix(night, _darken(night, 0.20), t)

def get_zone_for_hour(hour: int) -> Zone:
    return ZONES.get(int(hour) % 24, Zone("Zone", "🟣", "Quest", ""))

def fmt_hour(hour: int) -> str:
    return f"{int(hour) % 24:02d}:00"
