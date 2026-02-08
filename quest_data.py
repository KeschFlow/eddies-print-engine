# quest_data.py
# ==========================================================
# QUEST DATABASE (Single Source of Quest Truth)
# - Zones: thematische Lernwelten
# - Missions: sportlich-körperliche Aktivierung + Denkauftrag
# - XP: Progress ohne Wettbewerb (kein Ranking)
# ==========================================================

from dataclasses import dataclass
from typing import List, Dict
import random

@dataclass(frozen=True)
class Mission:
    id: str
    title: str
    movement: str        # sportliche Aufgabe (ortsunabhängig)
    thinking: str        # Denkteil (konvergentes Ziel, mehrere Wege)
    proof: str           # Nachweis (Haken/Unterschrift/Code)
    xp: int
    difficulty: int      # 1..5

@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    tagline: str
    missions: List[Mission]

# ---------------------------
# ZONEN (erweiterbar)
# ---------------------------

ZONES: List[Zone] = [
    Zone(
        id="zone_focus",
        name="Focus Zone",
        tagline="Körper an – Kopf klar.",
        missions=[
            Mission(
                id="fz_01",
                title="Balance-Reset",
                movement="30 Sekunden auf einem Bein stehen (rechts). Dann 30 Sekunden (links).",
                thinking="ZIEL: Finde 2 verschiedene Wege, ein Problem zu lösen. Schreibe/zeichne zwei Strategien.",
                proof="✅ Eltern/Lehrer: Initialen oder Code",
                xp=15,
                difficulty=1
            ),
            Mission(
                id="fz_02",
                title="Koordinations-Kick",
                movement="20 Hampelmänner ODER 20 Armkreise (Alternative).",
                thinking="ZIEL: Setze ein Muster fort (mind. 6 Schritte) UND erfinde ein neues Muster, das auch passt.",
                proof="✅ Haken + 1 Satz: „Meine neue Regel ist …“",
                xp=20,
                difficulty=2
            ),
            Mission(
                id="fz_03",
                title="Atem & Plan",
                movement="10 tiefe Atemzüge (4 Sekunden ein, 4 Sekunden aus) + 10 Kniebeugen (oder Wand-Kniebeugen).",
                thinking="ZIEL: Plane zwei Wege zum gleichen Ziel: 1) schnell 2) sicher. Zeichne beide Wege.",
                proof="✅ Skizze + Initialen",
                xp=25,
                difficulty=2
            ),
        ],
    ),
    Zone(
        id="zone_strategy",
        name="Strategy Zone",
        tagline="Mehrere Wege, ein Ziel.",
        missions=[
            Mission(
                id="sz_01",
                title="Sprint-Plan",
                movement="3×: 10 Sekunden schnell auf der Stelle laufen, dazwischen 20 Sekunden Pause.",
                thinking="ZIEL: Finde 2 unterschiedliche Lösungen für ein Regel-Rätsel. Erkläre den Unterschied.",
                proof="✅ 2 Lösungen markiert (A/B) + Initialen",
                xp=25,
                difficulty=3
            ),
            Mission(
                id="sz_02",
                title="Wall-Push",
                movement="10 Wand-Liegestütze (Alternative: 10 Schulter-Taps im Stehen).",
                thinking="ZIEL: Optimiere: Nimm eine Lösung und mache sie kürzer/eleganter. Zeichne Variante 2.",
                proof="✅ „Variante 2“ eingezeichnet",
                xp=30,
                difficulty=3
            ),
            Mission(
                id="sz_03",
                title="Team-Boost",
                movement="Zu zweit: 20 Sekunden synchron klatschen (Rhythmus) ODER 20 Sekunden Spiegel-Bewegung.",
                thinking="ZIEL: Erkläre einem anderen Kind deinen Lösungsweg. Danach findet ihr zusammen eine zweite Lösung.",
                proof="✅ Beide Namen + Initialen",
                xp=35,
                difficulty=4
            ),
        ],
    ),
    Zone(
        id="zone_build",
        name="Build Zone",
        tagline="Bauen, drehen, neu denken.",
        missions=[
            Mission(
                id="bz_01",
                title="Formen-Jäger",
                movement="Finde im Raum 3 Formen (Kreis, Dreieck, Rechteck) und zeichne sie schnell ab.",
                thinking="ZIEL: Baue aus 4 Teilen eine Form – und dann eine andere Form mit denselben Teilen.",
                proof="✅ 2 Formen gezeichnet",
                xp=30,
                difficulty=3
            ),
            Mission(
                id="bz_02",
                title="Stabilitätstest",
                movement="20 Sekunden Plank (Alternative: 20 Sekunden „Stuhl an der Wand“ oder 20 Sekunden auf Zehenspitzen).",
                thinking="ZIEL: Entwirf 2 Brücken-Designs (Zeichnung), die Punkt A mit Punkt B verbinden.",
                proof="✅ 2 Designs (A/B) + Initialen",
                xp=35,
                difficulty=4
            ),
            Mission(
                id="bz_03",
                title="Final Quest",
                movement="10 Kniebeugen + 10 Armkreise + 10 Sekunden Balance (frei wählbar).",
                thinking="ZIEL: Erfinde deine eigene Aufgabe: gleiches Ziel, andere Regeln, mehrere Lösungswege.",
                proof="✅ Aufgabe + 1 Beispiel-Lösung",
                xp=50,
                difficulty=5
            ),
        ],
    ),
]

# ---------------------------
# HELPER: Auswahl & Progress
# ---------------------------

def get_zones() -> List[Dict]:
    return [{"id": z.id, "name": z.name, "tagline": z.tagline} for z in ZONES]

def find_zone(zone_id: str) -> Zone:
    for z in ZONES:
        if z.id == zone_id:
            return z
    return ZONES[0]

def pick_mission(zone_id: str, difficulty: int, seed: int) -> Mission:
    z = find_zone(zone_id)
    rng = random.Random(seed)

    pool = [m for m in z.missions if m.difficulty <= difficulty]
    if not pool:
        pool = z.missions

    return rng.choice(pool)
