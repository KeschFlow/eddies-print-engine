# kern/kdp_preflight.py
from __future__ import annotations

from typing import Callable, List, Dict, Any
from reportlab.pdfgen.canvas import Canvas

# Jede Seite ist eine Funktion: (canvas, ctx) -> None, die genau 1 showPage() NICHT selbst aufruft
PageFn = Callable[[Canvas, Dict[str, Any]], None]

def ensure_min_pages(
    pages: List[PageFn],
    *,
    min_pages: int = 24,
    make_reflection_page: Callable[[int], PageFn],
) -> List[PageFn]:
    """
    KDP Hardening:
    - garantiert Mindestseitenzahl (default 24)
    - füllt mit hochwertigen Reflexionsseiten auf
    """
    out = list(pages or [])
    if min_pages <= 0:
        return out

    n = len(out)
    if n >= min_pages:
        return out

    # Fülle auf
    needed = min_pages - n
    start_idx = n + 1
    for k in range(needed):
        page_no = start_idx + k
        out.append(make_reflection_page(page_no))

    return out
