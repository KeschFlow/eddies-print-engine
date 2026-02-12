# =========================
# quest_data.py
# =========================
# ==========================================================
# QUEST DATABASE (Single Source of Quest Truth) — v2.3
# - Zones: 8 thematische Lernwelten (00-24h)
# - Missions: Sportliche Aktivierung + Denkauftrag
# - XP: Gamification ohne Wettbewerb
# - Cloud-safe API: compat (alte/neue app.py)
# ==========================================================

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import random


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
    time_ranges: List[Tuple[int, int]]
    color: Tuple[float, float, float]
    missions: List[Mission]


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


def get_zone_for_hour(hour: int) -> Zone:
    h = hour % 24
    for z in ZONES:
        for start, end in z.time_ranges:
            if start <= h < end:
                return z
    return ZONES[0]


def pick_mission_for_time(hour: int, difficulty: int, seed: int) -> Mission:
    z = get_zone_for_hour(hour)
    rng = random.Random(seed)

    pool = [m for m in z.missions if m.difficulty <= difficulty]
    if not pool:
        pool = z.missions

    return rng.choice(pool)


def fmt_hour(hour: int) -> str:
    return f"{hour % 24:02d}:00"


def get_hour_color(hour: int) -> Tuple[float, float, float]:
    h = hour % 24
    r, g, b = get_zone_for_hour(h).color

    if h >= 21 or h < 6:
        factor = 0.55
        r, g, b = r * factor, g * factor, b * factor

    r = max(0.0, min(1.0, r))
    g = max(0.0, min(1.0, g))
    b = max(0.0, min(1.0, b))
    return (r, g, b)


def validate_quest_db():
    issues = []
    zone_ids = [z.id for z in ZONES]
    if len(zone_ids) != len(set(zone_ids)):
        issues.append("Zone IDs sind nicht eindeutig.")
    mission_ids = [m.id for z in ZONES for m in z.missions]
    if len(mission_ids) != len(set(mission_ids)):
        issues.append("Mission IDs sind nicht eindeutig (global).")
    for z in ZONES:
        for m in z.missions:
            if not (1 <= m.difficulty <= 5):
                issues.append(f"Mission '{m.id}' difficulty außerhalb 1..5.")
    return issues


zone_for_hour = get_zone_for_hour
pick_mission = pick_mission_for_time