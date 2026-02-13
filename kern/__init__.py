# kern/__init__.py
"""
Zentraler Einstiegspunkt für den Kern der Eddie-Plattform.

WICHTIG:
- Dieses __init__.py muss in Deployments (z.B. Streamlit Cloud) stabil bleiben.
- Keine Imports, die optionalen Abhängigkeiten brauchen oder auf nicht vorhandene Module zeigen.
- App-Code soll bevorzugt explizit importieren, z.B.:
    from kern.export_orchestrator import run_export
"""

# Nur "sichere" Re-Exports (pdf_engine ist Kernbestandteil)
from .pdf_engine import (
    get_page_spec,
    draw_box,
    draw_writing_area,
    draw_brand_mark,
    draw_icon,
)

__all__ = [
    "get_page_spec",
    "draw_box",
    "draw_writing_area",
    "draw_brand_mark",
    "draw_icon",
]
