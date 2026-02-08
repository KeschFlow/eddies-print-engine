# quest_data.py
# ==========================================================
# PAPER-MMORPG WORLD / QUEST ENGINE
# - maps time-of-day to zones
# - picks a mission per page deterministically via seed
# ==========================================================

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
    atmosphere: str
    quest_type: str
    time_ranges: List[Tuple[int, int]]  # [start,end) hours, end exclusive
    missions: List[Mission]


ZONES: List[Zone] = [
    Zone(
        id="wachturm",
        name="🏰 Der Wachturm",
        atmosphere="Aufwachen, Struktur, Vorbereitung",
        quest_type="Skill Quest",
        time_ranges=[(6, 9)],
        missions=[
            Mission("wt_01","Rüstung anlegen","10 Kniebeugen ODER 10 Wand-Kniebeugen.",
                    "ZIEL: Plane 2 Wege für den Start (schnell vs. ruhig).",
                    "✅ Haken + (optional) Initialen", 15, 1),
            Mission("wt_02","Fokus-Reset","30s Balance rechts + 30s Balance links.",
                    "ZIEL: Nenne 2 Start-Schritte, die dich ins Tun bringen (A/B).",
                    "✅ A/B notieren", 20, 2),
        ],
    ),
    Zone(
        id="wilder_pfad",
        name="🌲 Der Wilde Pfad",
        atmosphere="Erkunden, Beobachten, Umgebung",
        quest_type="Exploration",
        time_ranges=[(9, 12)],
        missions=[
            Mission("wp_01","Musterjäger","20 Hampelmänner ODER 20 Schulter-Taps.",
                    "ZIEL: Finde 3 Muster (Form/Rhythmus/Wiederholung) und skizziere sie.",
                    "✅ 3 Skizzen", 25, 2),
            Mission("wp_02","Zwei Wege","3× 10s Lauf auf der Stelle, 20s Pause.",
                    "ZIEL: Zeichne 2 Wege zum gleichen Ziel (A/B) und vergleiche.",
                    "✅ Route A + B", 30, 3),
        ],
    ),
    Zone(
        id="taverne",
        name="🍲 Die Taverne",
        atmosphere="Essen, Pause, Energie",
        quest_type="Energy Quest",
        time_ranges=[(12, 13)],
        missions=[
            Mission("tv_01","Energie-Scan","10 langsame Kniebeugen + 10s still stehen.",
                    "ZIEL: Beschreibe 3 Sinnesdetails + 2 Wege zur Verbesserung (A/B).",
                    "✅ 3 Beobachtungen + A/B", 20, 1),
        ],
    ),
    Zone(
        id="werkstatt",
        name="🔨 Die Werkstatt",
        atmosphere="Bauen, Erschaffen, Spielen",
        quest_type="Build Quest",
        time_ranges=[(13, 15)],
        missions=[
            Mission("ws_01","Brückenbauer","20 Armkreise + 10 Schulterrollen.",
                    "ZIEL: Entwirf 2 Brücken-Designs (A/B) für Punkt A→B.",
                    "✅ Design A + B", 30, 3),
        ],
    ),
    Zone(
        id="arena",
        name="⚔️ Die Arena",
        atmosphere="Toben, Sport, Action",
        quest_type="Action Quest",
        time_ranges=[(15, 17)],
        missions=[
            Mission("ar_01","Speed-Runde","30s Lauf ODER 30s Schattenboxen.",
                    "ZIEL: Löse mit 2 Wegen: direkt vs. sicherer Umweg.",
                    "✅ 2 Wege skizzieren", 35, 3),
        ],
    ),
    Zone(
        id="ratssaal",
        name="🤝 Der Ratssaal",
        atmosphere="Helfen, Familie, Kooperation",
        quest_type="Social/Helper Quest",
        time_ranges=[(17, 19)],
        missions=[
            Mission("rs_01","Helfer-Quest","10 Kniebeugen + 10 Armkreise.",
                    "ZIEL: Erkläre jemandem deinen Weg; gemeinsam findet ihr Weg 2.",
                    "✅ 2 Namen + Initialen", 45, 4),
        ],
    ),
    Zone(
        id="quellen",
        name="🛁 Die Quellen",
        atmosphere="Bad, Pflege, Routine",
        quest_type="Water Quest",
        time_ranges=[(19, 21)],
        missions=[
            Mission("qq_01","Routine-Designer","10 Wand-Liegestütze ODER 10 Kniebeugen.",
                    "ZIEL: 2 Abend-Routinen (kurz/lang) mit gleichem Ziel.",
                    "✅ kurz/lang notieren", 30, 3),
        ],
    ),
    Zone(
        id="trauminsel",
        name="🌙 Die Traum-Insel",
        atmosphere="Schlaf, Ruhe, Dunkelheit",
        quest_type="Silent Quest",
       time_ranges=[(21, 24), (0, 6)],
        missions=[
            Mission("ti_01","Traum-Plan","5 tiefe Atemzüge + 20s Ruhe.",
                    "ZIEL: Erfinde 2 Enden für eine Geschichte – beide plausibel.",
                    "✅ Ende A + B", 20, 1),
        ],
    ),
]


def zone_for_hour(hour: int) -> Zone:
    h = hour % 24
    for z in ZONES:
        for start, end in z.time_ranges:
            if start <= h < end:
                return z
    return ZONES[0]


def pick_mission(hour: int, difficulty: int, seed: int) -> Mission:
    z = zone_for_hour(hour)
    rng = random.Random(seed)
    pool = [m for m in z.missions if m.difficulty <= difficulty] or z.missions
    return rng.choice(pool)


def fmt_hour(hour: int) -> str:
    return f"{hour%24:02d}:00"
