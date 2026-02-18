from __future__ import annotations

import io
import hashlib
from typing import List, Optional, Dict, Any, Tuple

from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

try:
    import image_wash as iw
except Exception:
    iw = None


def _stable_seed(s: str) -> int:
    return int.from_bytes(hashlib.sha256(s.encode("utf-8")).digest()[:8], "big")


def _open_sanitized(img_bytes: bytes) -> Image.Image:
    if iw is not None and hasattr(iw, "wash_bytes_to_rgb"):
        return iw.wash_bytes_to_rgb(img_bytes)

    im = Image.open(io.BytesIO(img_bytes))
    im = ImageOps.exif_transpose(im).convert("RGB")
    out = io.BytesIO()
    im.save(out, format="JPEG", quality=92, optimize=True, progressive=True)
    out.seek(0)
    return Image.open(out).convert("RGB")


def _pick_indices(n_total: int, need: int, seed: int, hero_first: bool) -> List[int]:
    if n_total <= 0:
        return []
    out = []
    if hero_first:
        out.append(0)
    i = 0
    while len(out) < need:
        idx = (seed + i * 9973) % n_total
        if idx not in out:
            out.append(idx)
        i += 1
    return out[:need]


def _thumb_cached(
    cache: Dict[Tuple[str, int, int], Image.Image],
    img_bytes: bytes,
    w: int,
    h: int,
) -> Image.Image:
    hsh = hashlib.sha256(img_bytes).hexdigest()
    key = (hsh, w, h)
    if key in cache:
        return cache[key]
    im = _open_sanitized(img_bytes)
    im = ImageOps.fit(im, (w, h), method=Image.LANCZOS, centering=(0.5, 0.5))
    cache[key] = im
    # cap cache size (simple LRU-ish by pop oldest insertion)
    if len(cache) > 96:
        cache.pop(next(iter(cache)))
    return im


def _render_template(
    *,
    uploads: List[Any],
    seed_str: str,
    template: str,
    hero_first: bool,
) -> Image.Image:
    seed = _stable_seed(seed_str)
    cache: Dict[Tuple[str, int, int], Image.Image] = {}

    # canvas size (square)
    W = 2400
    bg = Image.new("RGB", (W, W), "white")

    # picks
    n_total = len(uploads or [])
    def get_bytes(i: int) -> bytes:
        up = uploads[i]
        return up.getvalue() if hasattr(up, "getvalue") else bytes(up)

    if n_total == 0:
        return bg

    if template == "GRID_3":
        grid, tile, gap = 3, 720, 18
        need = grid * grid
        idxs = _pick_indices(n_total, need, seed, hero_first)
        k = 0
        for r in range(grid):
            for c in range(grid):
                b = get_bytes(idxs[k]); k += 1
                im = _thumb_cached(cache, b, tile, tile)
                x = c * (tile + gap)
                y = r * (tile + gap)
                bg.paste(im, (x, y))
        return bg

    if template == "HERO_STRIP":
        # Big hero + bottom strip (5 tiles)
        idxs = _pick_indices(n_total, 1 + 5, seed, hero_first)
        hero_b = get_bytes(idxs[0])
        hero = _thumb_cached(cache, hero_b, W, int(W * 0.72))
        bg.paste(hero, (0, 0))

        strip_h = W - hero.size[1]
        tile = int((W - 4 * 14) / 5)
        y0 = hero.size[1]
        for j in range(5):
            b = get_bytes(idxs[1 + j])
            im = _thumb_cached(cache, b, tile, strip_h)
            x = j * (tile + 14)
            bg.paste(im, (x, y0))
        return bg

    # default: HERO_4 (hero + 4 tiles right column)
    idxs = _pick_indices(n_total, 1 + 4, seed, hero_first)
    hero_b = get_bytes(idxs[0])
    hero = _thumb_cached(cache, hero_b, int(W * 0.72), W)
    bg.paste(hero, (0, 0))

    col_w = W - hero.size[0]
    gap = 14
    tile_h = int((W - 3 * gap) / 4)
    for j in range(4):
        b = get_bytes(idxs[1 + j])
        im = _thumb_cached(cache, b, col_w, tile_h)
        x0 = hero.size[0]
        y0 = j * (tile_h + gap)
        bg.paste(im, (x0, y0))
    return bg


def build_cover_collage(
    *,
    name: str,
    pages: int,
    paper: str,
    uploads: Optional[List[Any]],
    trim_in: float,
    bleed_in: float,
    paper_factors: Dict[str, float],
    spine_text_min_pages: int,
    purple_hex: str,
    template: str = "HERO_4",
    hero_first: bool = True,
    seed_extra: str = "",
) -> bytes:
    TRIM = trim_in * inch
    BLEED = bleed_in * inch

    factor = paper_factors.get(paper, 0.002252)
    sw = float(pages) * factor * inch
    sw = max(sw, 0.001 * inch)
    sw = round(sw / (0.001 * inch)) * (0.001 * inch)

    cw, ch = (2 * TRIM) + sw + (2 * BLEED), TRIM + (2 * BLEED)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(cw, ch))

    # base
    c.setFillColor(colors.white)
    c.rect(0, 0, cw, ch, fill=1, stroke=0)

    # spine
    c.setFillColor(colors.black)
    c.rect(BLEED + TRIM, BLEED, sw, TRIM, fill=1, stroke=0)

    if pages >= spine_text_min_pages:
        c.saveState()
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.translate(BLEED + TRIM + sw / 2, BLEED + TRIM / 2)
        c.rotate(90)
        c.drawCentredString(0, -4, f"EDDIES & {name}".upper())
        c.restoreState()

    # front area
    fx = BLEED + TRIM + sw
    fy = BLEED

    seed_str = f"{name}|{pages}|{paper}|{template}|{hero_first}|{seed_extra}"
    coll = _render_template(
        uploads=list(uploads or []),
        seed_str=seed_str,
        template=template,
        hero_first=hero_first,
    )

    # encode collage
    tmp = io.BytesIO()
    coll.save(tmp, format="JPEG", quality=88, optimize=True, progressive=True)
    tmp.seek(0)

    safe_in = 0.42
    pad = safe_in * inch
    title_band_h = 1.55 * inch

    coll_w = TRIM - 2 * pad
    coll_h = TRIM - 2 * pad - title_band_h

    c.drawImage(ImageReader(tmp), fx + pad, fy + pad, width=coll_w, height=coll_h, preserveAspectRatio=True)

    # title band
    c.setFillColor(colors.white)
    c.rect(fx + pad, fy + TRIM - pad - title_band_h, coll_w, title_band_h, fill=1, stroke=0)

    c.setStrokeColor(colors.HexColor(purple_hex))
    c.setLineWidth(3)
    c.line(fx + pad, fy + TRIM - pad - title_band_h, fx + pad + coll_w, fy + TRIM - pad - title_band_h)

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 42)
    c.drawCentredString(fx + TRIM / 2, fy + TRIM - pad - 0.75 * inch, "EDDIES")
    c.setFont("Helvetica", 18)
    c.drawCentredString(fx + TRIM / 2, fy + TRIM - pad - 1.20 * inch, f"& {name}")

    # back cover: minimal premium block
    bx = BLEED
    by = BLEED
    c.setFillColor(colors.white)
    c.rect(bx, by, TRIM, TRIM, fill=1, stroke=0)

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(bx + pad, by + TRIM - pad - 0.35*inch, "24 Stunden. 24 Missionen.")
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.Color(0.25,0.25,0.25))
    txt = c.beginText(bx + pad, by + TRIM - pad - 0.75*inch)
    txt.setLeading(14)
    for line in [
        "Dein Kind wird zum Helden: Aus euren Fotos werden Ausmalbilder,",
        "dazu kleine Quests (Bewegung + Denken) und XP zum Abhaken.",
        "",
        "• Personalisiert aus euren Uploads",
        "• KDP-ready Layout (Bleed + Safe)",
        "• Schwarzweiß, druckoptimiert",
        "",
        "Eddies Welt © 2026",
    ]:
        txt.textLine(line)
    c.drawText(txt)

    c.save()
    buf.seek(0)
    return buf.getvalue()
