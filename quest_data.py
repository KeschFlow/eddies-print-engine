# =========================
# quest_data.py  (Platinum v3.1)
# =========================
# ==========================================================
# QUEST DATABASE (Single Source of Quest Truth)
# - Zones: thematische Lernwelten (00–24h)
# - Missions: Bewegung + Denken + Proof + XP
# - Difficulty: 1..5
# - Audience Modes: kid/adult/senior via text-adapter
# - Cloud-safe API: compat mit app.py
#   (get_zone_for_hour, get_hour_color, pick_mission_for_time, fmt_hour, validate_quest_db)
# ==========================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Literal, Dict, Iterable
import random
import re

Audience = Literal["kid", "adult", "senior"]


# ----------------------------------------------------------
# Models
# ----------------------------------------------------------
@dataclass(frozen=True)
class Mission:
    id: str
    title: str
    movement: str
    thinking: str
    proof: str
    xp: int
    difficulty: int  # 1..5


@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    icon: str
    atmosphere: str
    quest_type: str
    time_ranges: List[Tuple[int, int]]  # hours as ints, end is exclusive
    color: Tuple[float, float, float]  # RGB 0..1
    missions: List[Mission]


# ----------------------------------------------------------
# DB
# ----------------------------------------------------------
ZONES: List[Zone] = [
    Zone(
        id="wachturm",
        name="Der Wachturm",
        icon="🏰",
        atmosphere="Aufwachen, Struktur",
        quest_type="Skill Quest",
        time_ranges=[(6, 9)],
        color=(0.95, 0.95, 0.85),
        missions=[
            Mission("wt_01", "Rüstung anlegen", "10 Kniebeugen.", "ZIEL: Plane 2 Wege, dich morgens fertig zu machen.", "✅ Haken", 15, 1),
            Mission("wt_02", "Fokus-Reset", "30s auf einem Bein stehen.", "ZIEL: Finde 2 Strategien für einen guten Start.", "✅ Notiz", 20, 2),
            Mission("wt_03", "Zahn-Monster", "2 Min Zähne putzen + 10 Hampelmänner.", "ZIEL: Besiege die Bakterien.", "✅ Sauberes Lächeln", 20, 1),
        ],
    ),
    Zone(
        id="wilder_pfad",
        name="Wilder Pfad",
        icon="🌲",
        atmosphere="Weg, Draußen, Erkunden",
        quest_type="Exploration",
        time_ranges=[(9, 12)],
        color=(0.85, 0.95, 0.85),
        missions=[
            Mission("wp_01", "Musterjäger", "Finde 3 rote Dinge und berühre sie.", "ZIEL: Zeichne ein Muster, das du siehst.", "✅ Skizze", 25, 2),
            Mission("wp_02", "Spurenleser", "Gehe 20 Schritte rückwärts.", "ZIEL: Finde einen Weg von A nach B.", "✅ Karte zeichnen", 30, 3),
        ],
    ),
    Zone(
        id="taverne",
        name="Die Taverne",
        icon="🍲",
        atmosphere="Essen, Energie tanken",
        quest_type="Energy Quest",
        time_ranges=[(12, 13)],
        color=(1.0, 0.9, 0.8),
        missions=[
            Mission("tv_01", "Energie-Scan", "10x Kauen pro Bissen.", "ZIEL: Errate 3 Zutaten im Essen.", "✅ Liste", 20, 1),
            Mission("tv_02", "Wasser-Kraft", "Trinke ein Glas Wasser.", "ZIEL: Fühle, wie die Energie zurückkommt.", "✅ Check", 15, 1),
        ],
    ),
    Zone(
        id="werkstatt",
        name="Die Werkstatt",
        icon="🔨",
        atmosphere="Bauen, Kreativität",
        quest_type="Build Quest",
        time_ranges=[(13, 15)],
        color=(0.9, 0.9, 1.0),
        missions=[
            Mission("ws_01", "Brückenbauer", "20 Armkreise.", "ZIEL: Baue eine Brücke aus Dingen im Raum.", "✅ Foto/Skizze", 30, 3),
            Mission("ws_02", "Turm-Ingenieur", "10 Liegestütze an der Wand.", "ZIEL: Baue den höchsten Turm.", "✅ Höhe messen", 35, 4),
        ],
    ),
    Zone(
        id="arena",
        name="Die Arena",
        icon="⚔️",
        atmosphere="Sport, Action",
        quest_type="Action Quest",
        time_ranges=[(15, 17)],
        color=(1.0, 0.85, 0.85),
        missions=[
            Mission("ar_01", "Schatten-Boxen", "30s Boxen in die Luft.", "ZIEL: Sei schneller als dein Schatten.", "✅ Puls fühlen", 35, 3),
            Mission("ar_02", "Lava-Boden", "Berühre 1 Min nicht den Boden.", "ZIEL: Finde einen sicheren Weg.", "✅ Geschafft", 40, 4),
        ],
    ),
    Zone(
        id="ratssaal",
        name="Der Ratssaal",
        icon="🤝",
        atmosphere="Sozial, Familie, Helfen",
        quest_type="Social Quest",
        time_ranges=[(17, 19)],
        color=(0.95, 0.85, 0.95),
        missions=[
            Mission("rs_01", "Der Bote", "Überbringe eine Nachricht flüsternd.", "ZIEL: Mache jemanden glücklich.", "✅ Lächeln erhalten", 45, 4),
            Mission("rs_02", "Tisch-Ritter", "Decke den Tisch in unter 2 Min.", "ZIEL: Helfen ist Ehrensache.", "✅ Alles am Platz", 40, 3),
        ],
    ),
    Zone(
        id="quellen",
        name="Die Quellen",
        icon="🛁",
        atmosphere="Bad, Hygiene",
        quest_type="Water Quest",
        time_ranges=[(19, 21)],
        color=(0.8, 0.95, 1.0),
        missions=[
            Mission("qq_01", "Schaum-Krone", "Wasche dein Gesicht.", "ZIEL: Werde sauber für die Nacht.", "✅ Spiegel-Check", 25, 2),
            Mission("qq_02", "Zahn-Schutz", "3 Min Putzen.", "ZIEL: Keine Chance für Karius.", "✅ Sauber", 25, 2),
        ],
    ),
    Zone(
        id="trauminsel",
        name="Traum-Insel",
        icon="🌙",
        atmosphere="Schlaf, Ruhe",
        quest_type="Silent Quest",
        time_ranges=[(21, 24), (0, 6)],
        color=(0.15, 0.15, 0.35),
        missions=[
            Mission("ti_01", "Traum-Fänger", "Augen zu, tief atmen.", "ZIEL: Erinnere dich an das Beste heute.", "✅ Gedanke", 20, 1),
            Mission("ti_02", "Stille Wacht", "Liege 1 Min ganz still.", "ZIEL: Lausche in die Nacht.", "✅ Ruhe", 20, 1),
        ],
    ),
]


# ----------------------------------------------------------
# Internal utilities (faster + safer)
# ----------------------------------------------------------
_WS = re.compile(r"\s+")

def _clean(s: str) -> str:
    return _WS.sub(" ", (s or "")).strip()

def _h(hour: int) -> int:
    return int(hour) % 24

def _in_range(h: int, start: int, end: int) -> bool:
    """
    Supports normal ranges (start<end) and wrap ranges (start>end).
    End is exclusive.
    Examples:
      (6,9)   covers 6,7,8
      (21,24) covers 21,22,23
      (22,2)  covers 22,23,0,1
    """
    start = int(start) % 24
    end = int(end) % 24
    if start == end:
        return True  # treat as full-day (rare but safe)
    if start < end:
        return start <= h < end
    return (h >= start) or (h < end)


# Precompute hour->zone for speed + deterministic fallback
_HOUR_TO_ZONE: Dict[int, Zone] = {}
for hr in range(24):
    z_found = None
    for z in ZONES:
        for a, b in z.time_ranges:
            if _in_range(hr, a, b):
                z_found = z
                break
        if z_found:
            break
    _HOUR_TO_ZONE[hr] = z_found if z_found else ZONES[0]


# ----------------------------------------------------------
# Audience adapters (text only, DB bleibt klein)
# ----------------------------------------------------------
def _adultize(m: Mission) -> Mission:
    movement = _clean(
        m.movement
        .replace("Hampelmänner", "lockere Sprünge (oder zügig gehen)")
        .replace("Kniebeugen", "Kniebeugen (oder 1 Minute zügig gehen)")
        .replace("Liegestütze an der Wand", "Wandstütz-Übung (sanft)")
        .replace("flüsternd", "leise und freundlich")
    )
    thinking = _clean(
        m.thinking
        .replace("ZIEL:", "REFLEXION:")
        .replace("Besiege", "Reduziere")
        .replace("Finde", "Notiere")
        .replace("Errate", "Identifiziere")
    )
    proof = _clean(m.proof.replace("✅", "☑️"))
    title = _clean(m.title)
    return Mission(m.id, title, movement, thinking, proof, int(m.xp), int(m.difficulty))


def _seniorize(m: Mission) -> Mission:
    movement = _clean(
        m.movement
        .replace("10 Kniebeugen.", "5 langsame Kniebeugen ODER 1 Minute im Raum gehen.")
        .replace("20 Armkreise.", "10 sanfte Armkreise (oder Schultern locker kreisen).")
        .replace("30s auf einem Bein stehen.", "10 Sekunden stabil stehen (am Tisch festhalten erlaubt).")
        .replace("30s Boxen in die Luft.", "30 Sekunden Arme sanft vor/zurück bewegen.")
        .replace("Berühre 1 Min nicht den Boden.", "1 Minute Sitz- oder Steh-Parcours (sicher!).")
        .replace("10x Kauen pro Bissen.", "Langsam kauen und bewusst schmecken.")
        .replace("Gehe 20 Schritte rückwärts.", "5 Schritte rückwärts (nur wenn sicher) ODER seitwärts gehen.")
    )
    thinking = _clean(
        m.thinking
        .replace("ZIEL:", "ERINNERUNG:")
        .replace("Plane", "Erinnere dich an")
        .replace("Finde", "Denke an")
        .replace("Zeichne", "Beschreibe")
        .replace("Errate", "Nenne")
    )
    # Ensure prefix only once
    if not thinking.startswith("ERINNERUNG:"):
        thinking = _clean("ERINNERUNG: " + thinking)

    proof = _clean(
        m.proof
        .replace("✅", "☑️")
        .replace("Foto/Skizze", "Notiz")
        .replace("Skizze", "Notiz")
    )
    title = _clean(m.title)
    return Mission(m.id, title, movement, thinking, proof, int(m.xp), int(m.difficulty))


def adapt_mission(m: Mission, audience: Audience) -> Mission:
    if audience == "kid":
        return m
    if audience == "adult":
        return _adultize(m)
    return _seniorize(m)


# ----------------------------------------------------------
# Public API (compat)
# ----------------------------------------------------------
def get_zone_for_hour(hour: int) -> Zone:
    """Fast & robust: uses precomputed mapping."""
    return _HOUR_TO_ZONE[_h(hour)]


def fmt_hour(hour: int) -> str:
    return f"{_h(hour):02d}:00"


def get_hour_color(hour: int) -> Tuple[float, float, float]:
    """
    Returns RGB 0..1.
    Night hours are slightly darkened for better mood-fit.
    """
    h = _h(hour)
    r, g, b = get_zone_for_hour(h).color

    # darker at night
    if h >= 21 or h < 6:
        factor = 0.55
        r, g, b = r * factor, g * factor, b * factor

    r = max(0.0, min(1.0, float(r)))
    g = max(0.0, min(1.0, float(g)))
    b = max(0.0, min(1.0, float(b)))
    return (r, g, b)


def pick_mission_for_time(
    hour: int,
    difficulty: int,
    seed: int,
    audience: Audience = "kid",
) -> Mission:
    """
    Deterministic pick:
    - chooses zone by time
    - filters missions by difficulty <= target (fallback: full zone)
    - adapts text for audience (kid/adult/senior)
    """
    z = get_zone_for_hour(hour)
    rng = random.Random(int(seed))

    d = max(1, min(5, int(difficulty)))
    pool = [m for m in z.missions if int(m.difficulty) <= d] or list(z.missions)

    chosen = rng.choice(pool)
    return adapt_mission(chosen, audience)


def validate_quest_db() -> List[str]:
    """
    Stronger validation:
    - unique IDs
    - difficulty 1..5
    - time-ranges valid
    - at least one zone per hour (coverage)
    """
    issues: List[str] = []

    # Unique zone IDs
    zone_ids = [z.id for z in ZONES]
    if len(zone_ids) != len(set(zone_ids)):
        issues.append("Zone IDs sind nicht eindeutig.")

    # Unique mission IDs (global)
    mission_ids = [m.id for z in ZONES for m in z.missions]
    if len(mission_ids) != len(set(mission_ids)):
        issues.append("Mission IDs sind nicht eindeutig (global).")

    # Mission difficulty bounds
    for z in ZONES:
        for m in z.missions:
            if not (1 <= int(m.difficulty) <= 5):
                issues.append(f"Mission '{m.id}' difficulty außerhalb 1..5.")

    # Time ranges validity
    for z in ZONES:
        if not z.time_ranges:
            issues.append(f"Zone '{z.id}' hat keine time_ranges.")
        for a, b in z.time_ranges:
            if not isinstance(a, int) or not isinstance(b, int):
                issues.append(f"Zone '{z.id}' time_ranges müssen int sein: {(a, b)}")
            # allow wrap; just sanity check
            if not (0 <= (a % 24) <= 23) or not (0 <= (b % 24) <= 23) and b != 24:
                issues.append(f"Zone '{z.id}' time_range ungültig: {(a, b)}")

    # Coverage check
    uncovered = []
    for hr in range(24):
        z = _HOUR_TO_ZONE.get(hr)
        if z is None:
            uncovered.append(hr)
    if uncovered:
        issues.append(f"Nicht alle Stunden abgedeckt: {uncovered}")

    return issues


# Backwards-compatible aliases
zone_for_hour = get_zone_for_hour
pick_mission = pick_mission_for_time