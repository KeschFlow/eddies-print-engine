from __future__ import annotations
import io
from PIL import Image, ImageOps, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

def wash_image_bytes(raw: bytes) -> bytes:
    if not raw:
        raise ValueError("empty upload")

    with Image.open(io.BytesIO(raw)) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        elif im.mode == "L":
            im = im.convert("RGB")
        
        out = io.BytesIO()
        im.save(out, format="PNG", optimize=True)
        return out.getvalue()

def wash_bytes(raw: bytes) -> bytes:
    return wash_image_bytes(raw)
