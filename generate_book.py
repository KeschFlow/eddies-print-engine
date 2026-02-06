from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import random
import os

# --- KONFIGURATION (KDP READY) ---
OUTPUT_DIR = "output"
PDF_NAME = "mein_erstes_kinderbuch.pdf"
PAGE_WIDTH, PAGE_HEIGHT = 8.5 * inch, 11 * inch  # Exaktes KDP Format
MARGIN = 0.75 * inch  # Sicherheitsabstand für den Druck

def draw_safe_zone(c):
    """Optional: Zeichnet einen sehr hellen Rahmen als Design-Element."""
    c.setLineWidth(0.5)
    c.setStrokeColorRGB(0.9, 0.9, 0.9)
    c.rect(MARGIN, MARGIN, PAGE_WIDTH - 2*MARGIN, PAGE_HEIGHT - 2*MARGIN)

def draw_connect_the_dots(c):
    """Punkt-zu-Punkt Logik (Mehrwert: Formen erkennen)."""
    points = []
    num_dots = random.randint(8, 15)
    for i in range(num_dots):
        x = random.uniform(MARGIN + 0.5*inch, PAGE_WIDTH - MARGIN - 0.5*inch)
        y = random.uniform(MARGIN + 0.5*inch, PAGE_HEIGHT - MARGIN - 0.5*inch)
        points.append((x, y))
    
    for i, (x, y) in enumerate(points):
        c.circle(x, y, 2, stroke=1, fill=1)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x + 5, y - 5, str(i + 1))

def draw_count_shapes(c):
    """Logik: Zählen und Formen erkennen (Ohne Text)."""
    shape_types = ["circle", "rect"]
    target_shape = random.choice(shape_types)
    count = 0
    
    for _ in range(12):
        stype = random.choice(shape_types)
        x = random.uniform(MARGIN + 0.5*inch, PAGE_WIDTH - MARGIN - 0.5*inch)
        y = random.uniform(MARGIN + 1.5*inch, PAGE_HEIGHT - MARGIN - 0.5*inch)
        size = random.uniform(0.3*inch, 0.7*inch)
        
        if stype == "circle":
            c.circle(x, y, size/2, stroke=1, fill=0)
        else:
            c.rect(x, y, size, size, stroke=1, fill=0)
        
        if stype == target_shape:
            count += 1

    # Bereich zum Eintragen der Lösung unten
    c.setLineWidth(1)
    if target_shape == "circle":
        c.circle(PAGE_WIDTH/2 - 20, MARGIN + 0.5*inch, 10, stroke=1)
    else:
        c.rect(PAGE_WIDTH/2 - 30, MARGIN + 0.4*inch, 20, 20, stroke=1)
    
    c.setFont("Helvetica", 14)
    c.drawString(PAGE_WIDTH/2, MARGIN + 0.5*inch, "= ____")

def generate_book(pages=30):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, PDF_NAME)
    c = canvas.Canvas(path, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))

    for i in range(1, pages + 1):
        draw_safe_zone(c)
        
        # Zufällige Wahl zwischen den Aktivitäten
        activity = random.choice(["dots", "count"])
        if activity == "dots":
            draw_connect_the_dots(c)
        else:
            draw_count_shapes(c)
            
        c.showPage()
    
    c.save()
    print(f"--- FERTIG: {pages} Seiten generiert in {path} ---")

if __name__ == "__main__":
    generate_book(30)
