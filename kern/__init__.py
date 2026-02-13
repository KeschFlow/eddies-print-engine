# kern/__init__.py
"""
Zentraler Einstiegspunkt für den Kern der Eddies-Plattform.

Wichtig:
- Dieses Package-Init darf KEINE Imports enthalten, die im Deployment fehlen.
- In Streamlit Cloud bricht sonst jeder Import von `kern.*` sofort ab.

Du kannst hier bewusst nur die stabilen, tatsächlich vorhandenen Funktionen re-exportieren.
"""

# PDF-Engine – stabile, vorhandene Funktionen
from .pdf_engine import (
    get_page_spec,       # Seitenformat & Margins (A4 / KDP)
    draw_box,            # Boxen / Rahmen
    draw_writing_area,   # Schreibflächen (Linien optional)
    draw_brand_mark,     # lila Zunge (Vektor-Wasserzeichen)
    draw_icon,           # Icon-Fallback / Registry-Hook
)

# Optional: Vokabel-Daten (nur wenn du es wirklich brauchst)
# from .subject_data import SUBJECTS, AUTO_ICON
