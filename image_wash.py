# =========================================================
# image_wash.py — Eddies Upload Sanitizer (FINAL)
# =========================================================

from __future__ import annotations
import io
from PIL import Image, ImageOps

MAX_SIDE = 10000


def wash_image(file) -> Image.Image:
    """
    Accepts Streamlit upload OR file-like object.
    Returns clean RGB PIL image.
    """

    if hasattr(file, "read"):
        b = file.read()
    else:
        b = file

    if not b:
        raise ValueError("empty image")

    bio = io.BytesIO(b)

    with Image.open(bio) as im:
        im.load()

        # EXIF orientation fix
        im = ImageOps.exif_transpose(im)

        # Clamp size
        w, h = im.size
        m = max(w, h)
        if m > MAX_SIDE:
            s = MAX_SIDE / float(m)
            im = im.resize((int(w*s), int(h*s)), Image.LANCZOS)

        # Normalize mode
        if im.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        elif im.mode != "RGB":
            im = im.convert("RGB")

        return im
