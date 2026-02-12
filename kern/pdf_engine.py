from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
import io

# Standard Print Geometry
TRIM = 8.5 * inch
BLEED = 0.125 * inch
SAFE = 0.375 * inch


def get_geometry(kdp_mode=True):
    if kdp_mode:
        page_w = TRIM + 2 * BLEED
        page_h = TRIM + 2 * BLEED
        safe = BLEED + SAFE
    else:
        page_w = TRIM
        page_h = TRIM
        safe = SAFE

    return page_w, page_h, safe


def draw_brand_mark(c: canvas.Canvas, cx, cy, r):
    c.saveState()
    c.setLineWidth(3)
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.white)
    c.circle(cx, cy, r, stroke=1, fill=1)

    # Paw center
    c.setFillColor(colors.black)
    c.circle(cx, cy, r * 0.3, fill=1)

    # Toes
    c.circle(cx - r * 0.3, cy + r * 0.35, r * 0.18, fill=1)
    c.circle(cx + r * 0.3, cy + r * 0.35, r * 0.18, fill=1)
    c.circle(cx - r * 0.1, cy + r * 0.55, r * 0.15, fill=1)
    c.circle(cx + r * 0.1, cy + r * 0.55, r * 0.15, fill=1)

    c.restoreState()


def build_simple_vocab_pdf(subject_name, vocab_list):
    buffer = io.BytesIO()
    page_w, page_h, safe = get_geometry(False)
    c = canvas.Canvas(buffer, pagesize=(page_w, page_h))

    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(page_w / 2, page_h - safe, subject_name)

    y = page_h - safe - 60

    for item in vocab_list:
        c.setFont("Helvetica-Bold", 18)
        c.drawString(safe, y, item["wort"])

        y -= 25
        c.setFont("Helvetica", 14)
        c.drawString(safe + 20, y, item["satz"])

        y -= 40

        if y < safe:
            c.showPage()
            y = page_h - safe - 60

    c.save()
    buffer.seek(0)
    return buffer.getvalue()
