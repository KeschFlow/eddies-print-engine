# engine_sketch.py
# ==========================================================
# Minimal, stabile "Skizzen-Engine" (druckfreundlich)
# - erzeugt pro Seite eine Aktivitätsgrafik (Maze + Suchobjekte)
# - deterministic via seed
# ==========================================================

import random
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

def _draw_maze(c: canvas.Canvas, x: float, y: float, w: float, h: float, seed: int, cells_x: int = 10, cells_y: int = 14):
    rng = random.Random(seed)

    # Cell size
    cw = w / cells_x
    ch = h / cells_y

    # Maze walls (simple randomized grid walls)
    c.setLineWidth(1)

    # Outer border
    c.rect(x, y, w, h)

    # Internal walls
    for i in range(1, cells_x):
        # vertical wall segment with random gaps
        if rng.random() < 0.8:
            gap = rng.randint(0, cells_y - 1)
            for j in range(cells_y):
                if j == gap:
                    continue
                x0 = x + i * cw
                y0 = y + j * ch
                c.line(x0, y0, x0, y0 + ch)

    for j in range(1, cells_y):
        # horizontal wall segment with random gaps
        if rng.random() < 0.8:
            gap = rng.randint(0, cells_x - 1)
            for i in range(cells_x):
                if i == gap:
                    continue
                x0 = x + i * cw
                y0 = y + j * ch
                c.line(x0, y0, x0 + cw, y0)

    # Start/End markers
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y + h + 3*mm, "Start →")
    c.drawRightString(x + w, y + h + 3*mm, "→ Ziel")

    # Start/End circles
    c.circle(x + cw*0.5, y + ch*0.5, 3*mm, stroke=1, fill=0)
    c.circle(x + w - cw*0.5, y + h - ch*0.5, 3*mm, stroke=1, fill=0)

def _draw_seek_objects(c: canvas.Canvas, x: float, y: float, w: float, h: float, seed: int):
    rng = random.Random(seed + 999)

    # Draw small simple icons to find (circle, square, triangle)
    shapes = ["KREIS", "QUADRAT", "DREIECK"]
    targets = rng.sample(shapes, k=2)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y - 8*mm, f"Suchauftrag: Finde {targets[0]} und {targets[1]} im Labyrinth und markiere sie.")

    # Place random icons inside the area
    c.setLineWidth(1)
    for _ in range(18):
        sx = x + rng.random() * w
        sy = y + rng.random() * h
        t = rng.choice(shapes)

        if t == "KREIS":
            c.circle(sx, sy, 2.5*mm, stroke=1, fill=0)
        elif t == "QUADRAT":
            c.rect(sx - 2.5*mm, sy - 2.5*mm, 5*mm, 5*mm)
        else:  # triangle
            c.line(sx, sy + 3*mm, sx - 3*mm, sy - 3*mm)
            c.line(sx - 3*mm, sy - 3*mm, sx + 3*mm, sy - 3*mm)
            c.line(sx + 3*mm, sy - 3*mm, sx, sy + 3*mm)

def render_activity_page(c: canvas.Canvas, page_width: float, page_height: float, seed: int,
                         margin_left: float, margin_right: float, top_reserved: float, bottom_reserved: float):
    """
    Draws the base activity content inside the free content area.
    """
    # Free content area:
    x = margin_left
    y = bottom_reserved
    w = page_width - margin_left - margin_right
    h = page_height - top_reserved - bottom_reserved

    # Title line
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, page_height - top_reserved - 10*mm, "Aktivität: Labyrinth + Suchauftrag")

    # Maze area (leave some room for title)
    maze_y = y + 10*mm
    maze_h = h - 25*mm
    _draw_maze(c, x, maze_y, w, maze_h, seed=seed, cells_x=10, cells_y=14)
    _draw_seek_objects(c, x, maze_y, w, maze_h, seed=seed)
