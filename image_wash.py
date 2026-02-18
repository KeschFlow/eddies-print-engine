# =========================================================
# image_wash.py (Eddies 2026 — UPLOAD SANITIZER)
# - Fixes EXIF orientation issues
# - Converts weird modes to RGB
# - Re-encodes safely (JPEG or PNG)
# - Prevents broken/corrupt image bytes from crashing OpenCV/Pillow
# =========================================================
from __future__ import annotations

import io
from PIL import Image, ImageOps

MAX_SIDE = 10000  # safety; avoids absurdly huge images killing memory


def wash_image_bytes(b: bytes) -> bytes:
    """
    Returns sanitized bytes (JPEG) by default.
    - Load via Pillow
    - Apply EXIF transpose
    - Convert to RGB (strip alpha by compositing onto white)
    - Clamp size
    - Re-encode cleanly
    """
    if not b:
        raise ValueError("empty image bytes")

    bio = io.BytesIO(b)
    with Image.open(bio) as im:
        im.load()

        # fix EXIF rotation
        im = ImageOps.exif_transpose(im)

        # clamp size (safety)
        w, h = im.size
        m = max(w, h)
        if m > MAX_SIDE:
            scale = MAX_SIDE / float(m)
            im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        # normalize mode
        if im.mode in ("RGBA", "LA"):
            # composite on white
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        elif im.mode != "RGB":
            im = im.convert("RGB")

        out = io.BytesIO()
        # always output JPEG for predictable OpenCV decode
        im.save(out, format="JPEG", quality=95, optimize=True, progressive=True)
        out.seek(0)
        return out.getvalue()