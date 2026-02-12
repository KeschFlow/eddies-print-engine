# kern/subject_data.py
# Berufssprachliche Vokabeln – optimiert für DaZ / Integrationskurse

SUBJECTS = {
    "Schneidern": [
        {"wort": "die Nadel",      "satz": "Ich brauche eine neue Nadel zum Nähen."},
        {"wort": "der Stoff",      "satz": "Der Stoff ist weich und blau."},
        {"wort": "die Schere",     "satz": "Ich schneide den Stoff mit der Schere."},
        {"wort": "das Maßband",    "satz": "Ich messe die Länge mit dem Maßband."},
        {"wort": "der Reißverschluss", "satz": "Der Reißverschluss ist kaputt."},
        {"wort": "der Faden",      "satz": "Ich ziehe den Faden durch die Nadel."},
    ],
    "Pflege": [
        {"wort": "der Verband",    "satz": "Ich wechsle den Verband beim Patienten."},
        {"wort": "der Blutdruck",  "satz": "Wir messen jeden Morgen den Blutdruck."},
        {"wort": "die Pflegekraft", "satz": "Die Pflegekraft hilft beim Aufstehen."},
        {"wort": "das Fieber",     "satz": "Das Fieber ist auf 38,5 Grad gestiegen."},
        {"wort": "die Spritze",    "satz": "Ich bereite die Spritze für die Impfung vor."},
        {"wort": "der Rollstuhl",  "satz": "Ich schiebe den Rollstuhl zum Aufzug."},
    ],
    "Gastronomie": [
        {"wort": "die Speisekarte", "satz": "Die Speisekarte liegt auf dem Tisch."},
        {"wort": "der Kellner",    "satz": "Der Kellner nimmt die Bestellung auf."},
        {"wort": "das Trinkgeld",  "satz": "Vielen Dank für das Trinkgeld!"},
        {"wort": "die Rechnung",   "satz": "Hier ist Ihre Rechnung, bitte sehr."},
        {"wort": "der Teller",     "satz": "Ich stelle den Teller vor den Gast."},
        {"wort": "die Küche",      "satz": "In der Küche arbeiten zwei Köche."},
    ],
    # Neue Kategorien (optional – sofort nutzbar)
    "Büro & Verwaltung": [
        {"wort": "der Computer",   "satz": "Ich arbeite am Computer im Büro."},
        {"wort": "die Akte",       "satz": "Bitte bringen Sie die Akte mit."},
        {"wort": "der Termin",     "satz": "Der Termin ist um 14 Uhr."},
        {"wort": "die E-Mail",     "satz": "Ich schreibe eine E-Mail an den Chef."},
    ],
}

# Mapping: Kategorie / Schlüsselwort → Icon-Slug (aus pdf_engine.py)
# Kann später auch pro Vokabel überschrieben werden
AUTO_ICON = {
    # Schneidern
    "schneidern": "scissors",       # oder "needle"
    "nadel": "needle",              # wenn du später ein Nadel-Icon hast
    "stoff": "fabric",
    
    # Pflege
    "pflege": "medical_cross",
    "verband": "medical_cross",
    "blutdruck": "medical_cross",
    "spritze": "syringe",           # falls du später hinzufügst
    
    # Gastronomie
    "gastronomie": "fork_knife",
    "küche": "fork_knife",
    "koch": "fork_knife",
    "kellner": "tray",              # oder "waiter"
    
    # Büro
    "büro": "computer",
    "computer": "computer",
    "akte": "briefcase",
    
    # Generische Fallbacks
    "metall": "hammer",
    "werkzeug": "hammer",
    "werkstatt": "gear",
    "arzt": "medical_cross",
    "büro": "briefcase",
    "lehrer": "book_open",          # falls du später Bildung hinzufügst
}
