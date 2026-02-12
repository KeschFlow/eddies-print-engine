# engine_sketch.py
# ==========================================================
# Eddie – Platinum Activity Engine (druckfreundlich, stabil)
# - erzeugt pro Seite eine Aktivitätsgrafik (Maze + Suchobjekte)
# - deterministic via seed (keine global random side-effects)
# - robust gegen Rand-Überläufe (safe padding)
# - saubere LineWidths/Fonts für Druck
# ==========================================================

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Tuple

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors


# -----------------------------
# Konfig / Helpers
# -----------------------------
@dataclass(frozen=True)
class ActivityLayout:
    title: str = "Aktivität: Labyrinth + Suchauftrag"
    maze_cells_x: int = 10
    maze_cells_y: int = 14
    wall_density: float = 0.82      # 0..1 (mehr = mehr Wände)
    icons_count: int = 18
    marker_r_mm: float = 3.0
    icon_r_mm: float = 2.5
    safe_pad_mm: float = 2.5        # Abstand innerhalb der Maze-Box
    title_gap_mm: float = 10.0
    seek_text_gap_mm: float = 8.0
    min_cell_mm: float = 4.0        # Sicherheit, damit Zellen nicht zu klein werden


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _set_stroke(c: canvas.Canvas, lw: float = 1.0):
    c.setStrokeColor(colors.black)
    c.setLineWidth(max(0.6, lw))


def _set_text(c: canvas.Canvas):
    c.setFillColor(colors.black)


# -----------------------------
# Maze Rendering
# -----------------------------
def _draw_maze(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    rng: random.Random,
    cells_x: int,
    cells_y: int,
    wall_density: float,
    marker_r: float,
    safe_pad: float,
):
    """
    Simple randomized grid-walls maze.
    Deterministic via rng.
    (x,y) = lower-left of maze box
    """
    # Border
    _set_stroke(c, lw=1.0)
    c.rect(x, y, w, h, stroke=1, fill=0)

    # Ensure safe padding inside borders
    ix = x + safe_pad
    iy = y + safe_pad
    iw = max(1.0, w - 2 * safe_pad)
    ih = max(1.0, h - 2 * safe_pad)

    # Cell size (avoid too tiny)
    cx = max(2, int(cells_x))
    cy = max(2, int(cells_y))
    cw = iw / cx
    ch = ih / cy

    # If cells become too small, reduce grid automatically
    # (keeps printing readable)
    min_cell = 4 * mm
    while cw < min_cell and cx > 4:
        cx -= 1
        cw = iw / cx
    while ch < min_cell and cy > 4:
        cy -= 1
        ch = ih / cy

    # Internal walls
    # Vertical segments at each grid line i (1..cx-1)
    for i in range(1, cx):
        if rng.random() < wall_density:
            gap = rng.randint(0, cy - 1)
            x0 = ix + i * cw
            for j in range(cy):
                if j == gap:
                    continue
                y0 = iy + j * ch
                c.line(x0, y0, x0, y0 + ch)

    # Horizontal segments at each grid line j (1..cy-1)
    for j in range(1, cy):
        if rng.random() < wall_density:
            gap = rng.randint(0, cx - 1)
            y0 = iy + j * ch
            for i in range(cx):
                if i == gap:
                    continue
                x0 = ix + i * cw
                c.line(x0, y0, x0 + cw, y0)

    # Start/End markers (inside padding)
    _set_text(c)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y + h + 3 * mm, "Start →")
    c.drawRightString(x + w, y + h + 3 * mm, "→ Ziel")

    # Start/End circles
    _set_stroke(c, lw=1.0)
    sx = ix + cw * 0.5
    sy = iy + ch * 0.5
    ex = ix + iw - cw * 0.5
    ey = iy + ih - ch * 0.5
    c.circle(sx, sy, marker_r, stroke=1, fill=0)
    c.circle(ex, ey, marker_r, stroke=1, fill=0)


# -----------------------------
# Seek Objects Rendering
# -----------------------------
_SHAPES = ("KREIS", "QUADRAT", "DREIECK")


def _draw_triangle(c: canvas.Canvas, cx: float, cy: float, r: float):
    # Equilateral-ish
    c.line(cx, cy + r, cx - r, cy - r)
    c.line(cx - r, cy - r, cx + r, cy - r)
    c.line(cx + r, cy - r, cx, cy + r)


def _draw_seek_objects(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    rng: random.Random,
    icons_count: int,
    icon_r: float,
):
    # Pick 2 targets
    targets = rng.sample(list(_SHAPES), k=2)

    _set_text(c)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(
        x,
        y - 8 * mm,
        f"Suchauftrag: Finde {targets[0]} und {targets[1]} im Labyrinth und markiere sie.",
    )

    # Place random icons inside maze area
    _set_stroke(c, lw=1.0)

    # Keep icons away from edges a bit
    pad = max(3 * mm, icon_r * 1.5)
    x0 = x + pad
    y0 = y + pad
    x1 = x + w - pad
    y1 = y + h - pad

    for _ in range(max(1, int(icons_count))):
        sx = x0 + rng.random() * max(1.0, (x1 - x0))
        sy = y0 + rng.random() * max(1.0, (y1 - y0))
        t = rng.choice(_SHAPES)

        if t == "KREIS":
            c.circle(sx, sy, icon_r, stroke=1, fill=0)
        elif t == "QUADRAT":
            c.rect(sx - icon_r, sy - icon_r, 2 * icon_r, 2 * icon_r, stroke=1, fill=0)
        else:
            _draw_triangle(c, sx, sy, icon_r)


# -----------------------------
# Public API
# -----------------------------
def render_activity_page(
    c: canvas.Canvas,
    page_width: float,
    page_height: float,
    seed: int,
    *,
    margin_left: float,
    margin_right: float,
    top_reserved: float,
    bottom_reserved: float,
    layout: ActivityLayout | None = None,
):
    """
    Zeichnet die Aktivitätsseite in den freien Content-Bereich.

    Erwartung:
    - margin_left/right und top_reserved/bottom_reserved sind bereits "safe"
      (z.B. aus KDP safe-zone).
    """
    lay = layout or ActivityLayout()

    # Free content area
    x = float(margin_left)
    y = float(bottom_reserved)
    w = float(page_width) - float(margin_left) - float(margin_right)
    h = float(page_height) - float(top_reserved) - float(bottom_reserved)

    # Guard: falls zu klein, einfach nur Hinweis zeichnen
    if w < 30 * mm or h < 50 * mm:
        _set_text(c)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x, y + max(0, h - 20), "Aktivität (zu wenig Platz)")
        return

    rng = random.Random(int(seed))

    # Title
    _set_text(c)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, float(page_height) - float(top_reserved) - lay.title_gap_mm * mm, lay.title)

    # Maze area (unter dem Titel, genug Luft für Suchauftrag)
    # Wir lassen unten Platz für Suchtext (unter der Maze) -> daher Maze_y etwas höher
    maze_x = x
    maze_y = y + 12 * mm
    maze_w = w

    # Reserve: title area oben + seek text unter der maze
    maze_h = h - (28 * mm)
    maze_h = max(30 * mm, maze_h)

    safe_pad = lay.safe_pad_mm * mm
    marker_r = lay.marker_r_mm * mm
    icon_r = lay.icon_r_mm * mm

    _draw_maze(
        c,
        maze_x,
        maze_y,
        maze_w,
        maze_h,
        rng=rng,
        cells_x=lay.maze_cells_x,
        cells_y=lay.maze_cells_y,
        wall_density=_clamp(lay.wall_density, 0.0, 1.0),
        marker_r=marker_r,
        safe_pad=safe_pad,
    )

    # Seek objects use a shifted rng stream (no need for +999 seed, just consume rng deterministically)
    # Make a new rng derived from base seed to keep stable layout if you tweak maze calls later.
    rng_seek = random.Random(int(seed) ^ 0x9E3779B9)

    _draw_seek_objects(
        c,
        maze_x,
        maze_y,
        maze_w,
        maze_h,
        rng=rng_seek,
        icons_count=lay.icons_count,
        icon_r=icon_r,
    )