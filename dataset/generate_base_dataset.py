import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


BASE_DIR = Path(__file__).resolve().parent
GROUND_TRUTH_DIR = BASE_DIR / "ground_truth"
RAW_DIR = BASE_DIR / "raw"

FACTURE_DIR = RAW_DIR / "facture"
URSSAF_DIR = RAW_DIR / "urssaf"
RIB_DIR = RAW_DIR / "rib"
DEGRADED_DIR = RAW_DIR / "degraded"

PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT = 50
RIGHT = PAGE_WIDTH - 50
TOP = PAGE_HEIGHT - 50

IMG_WIDTH = 1240
IMG_HEIGHT = 1754
IMG_MARGIN_X = 80


def ensure_directories() -> None:
    FACTURE_DIR.mkdir(parents=True, exist_ok=True)
    URSSAF_DIR.mkdir(parents=True, exist_ok=True)
    RIB_DIR.mkdir(parents=True, exist_ok=True)
    DEGRADED_DIR.mkdir(parents=True, exist_ok=True)


def load_suppliers() -> list[dict]:
    suppliers_path = GROUND_TRUTH_DIR / "suppliers.json"
    with suppliers_path.open("r", encoding="utf-8") as file:
        return json.load(file)


# =========================
# PDF NORMALS - REPORTLAB
# =========================

def draw_page_header(pdf: canvas.Canvas, title: str, supplier: dict) -> float:
    y = TOP

    pdf.setFillColor(colors.HexColor("#1F2937"))
    pdf.rect(0, PAGE_HEIGHT - 90, PAGE_WIDTH, 90, fill=1, stroke=0)

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(LEFT, PAGE_HEIGHT - 45, title)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(LEFT, PAGE_HEIGHT - 65, f"Référence dossier : {supplier['supplier_id']}")
    pdf.drawString(LEFT + 220, PAGE_HEIGHT - 65, f"Scénario : {supplier['scenario']}")

    return PAGE_HEIGHT - 120


def draw_section_title(pdf: canvas.Canvas, title: str, y: float) -> float:
    pdf.setFillColor(colors.HexColor("#111827"))
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(LEFT, y, title)

    pdf.setStrokeColor(colors.HexColor("#D1D5DB"))
    pdf.line(LEFT, y - 6, RIGHT, y - 6)
    return y - 24


def draw_key_value_box(pdf: canvas.Canvas, items: list[tuple[str, str]], y: float) -> float:
    box_height = 24 * len(items) + 20
    pdf.setFillColor(colors.HexColor("#F9FAFB"))
    pdf.setStrokeColor(colors.HexColor("#D1D5DB"))
    pdf.roundRect(LEFT, y - box_height + 8, RIGHT - LEFT, box_height, 8, fill=1, stroke=1)

    current_y = y - 15
    for label, value in items:
        pdf.setFillColor(colors.HexColor("#374151"))
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(LEFT + 15, current_y, f"{label} :")

        pdf.setFont("Helvetica", 11)
        pdf.setFillColor(colors.black)
        pdf.drawString(LEFT + 170, current_y, value)

        current_y -= 24

    return y - box_height - 18


def create_invoice_pdf(path: Path, supplier: dict) -> None:
    pdf = canvas.Canvas(str(path), pagesize=A4)
    y = draw_page_header(pdf, "FACTURE FOURNISSEUR", supplier)

    y = draw_section_title(pdf, "Informations fournisseur", y)
    y = draw_key_value_box(pdf, [
        ("Fournisseur", supplier["supplier_name"]),
        ("SIRET", supplier["invoice_siret"]),
        ("TVA intracommunautaire", supplier["tva"])
    ], y)

    y = draw_section_title(pdf, "Informations de facturation", y)
    y = draw_key_value_box(pdf, [
        ("Date d'émission", supplier["date_emission"]),
        ("Montant HT", f"{supplier['montant_ht']:.2f} EUR"),
        ("Montant TTC", f"{supplier['montant_ttc']:.2f} EUR")
    ], y)

    pdf.setFont("Helvetica-Oblique", 10)
    pdf.setFillColor(colors.HexColor("#6B7280"))
    pdf.drawString(LEFT, 60, "Document généré pour tests de traitement documentaire.")
    pdf.save()


def create_urssaf_pdf(path: Path, supplier: dict) -> None:
    pdf = canvas.Canvas(str(path), pagesize=A4)
    y = draw_page_header(pdf, "ATTESTATION DE VIGILANCE URSSAF", supplier)

    y = draw_section_title(pdf, "Informations entreprise", y)
    y = draw_key_value_box(pdf, [
        ("Entreprise", supplier["supplier_name"]),
        ("SIRET", supplier["urssaf_siret"]),
        ("Date d'expiration", supplier["date_expiration"])
    ], y)

    pdf.setFont("Helvetica", 11)
    pdf.setFillColor(colors.black)
    pdf.drawString(LEFT, y, "Le présent document atteste de la régularité de la situation sociale.")
    pdf.drawString(LEFT, y - 18, "Ce document est utilisé dans un contexte de test hackathon.")
    pdf.save()


def create_rib_pdf(path: Path, supplier: dict) -> None:
    pdf = canvas.Canvas(str(path), pagesize=A4)
    y = draw_page_header(pdf, "RELEVÉ D'IDENTITÉ BANCAIRE", supplier)

    bic_value = supplier["rib_bic"] if supplier["rib_bic"] else "NON RENSEIGNÉ"

    y = draw_section_title(pdf, "Informations bancaires", y)
    y = draw_key_value_box(pdf, [
        ("Titulaire du compte", supplier["supplier_name"]),
        ("IBAN", supplier["rib_iban"]),
        ("BIC", bic_value)
    ], y)

    pdf.setFont("Helvetica", 11)
    pdf.setFillColor(colors.black)
    pdf.drawString(LEFT, y, "Merci de vérifier les coordonnées bancaires avant tout paiement.")
    pdf.save()


# =========================
# DEGRADED PDFS - PIL IMAGE -> PDF
# =========================

def get_fonts() -> tuple[ImageFont.ImageFont, ImageFont.ImageFont, ImageFont.ImageFont]:
    try:
        title_font = ImageFont.truetype("arial.ttf", 34)
        subtitle_font = ImageFont.truetype("arial.ttf", 22)
        text_font = ImageFont.truetype("arial.ttf", 24)
    except OSError:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    return title_font, subtitle_font, text_font


def create_base_image() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), "white")
    draw = ImageDraw.Draw(image)
    return image, draw


def draw_image_header(draw: ImageDraw.ImageDraw, supplier: dict, title: str, fonts: tuple) -> int:
    title_font, subtitle_font, _ = fonts

    draw.rectangle([(0, 0), (IMG_WIDTH, 140)], fill=(31, 41, 55))
    draw.text((IMG_MARGIN_X, 35), title, fill="white", font=title_font)
    draw.text(
        (IMG_MARGIN_X, 90),
        f"Reference dossier : {supplier['supplier_id']} | Scenario : {supplier['scenario']}",
        fill="white",
        font=subtitle_font,
    )
    return 190


def draw_image_section_title(draw: ImageDraw.ImageDraw, y: int, title: str, fonts: tuple) -> int:
    _, subtitle_font, _ = fonts
    draw.text((IMG_MARGIN_X, y), title, fill=(17, 24, 39), font=subtitle_font)
    draw.line((IMG_MARGIN_X, y + 35, IMG_WIDTH - IMG_MARGIN_X, y + 35), fill=(209, 213, 219), width=2)
    return y + 55


def draw_image_box(draw: ImageDraw.ImageDraw, y: int, items: list[tuple[str, str]], fonts: tuple) -> int:
    _, _, text_font = fonts
    box_height = 30 + len(items) * 48

    draw.rounded_rectangle(
        [(IMG_MARGIN_X, y), (IMG_WIDTH - IMG_MARGIN_X, y + box_height)],
        radius=12,
        outline=(209, 213, 219),
        width=2,
        fill=(249, 250, 251),
    )

    current_y = y + 18
    for label, value in items:
        draw.text((IMG_MARGIN_X + 20, current_y), f"{label} :", fill=(55, 65, 81), font=text_font)
        draw.text((IMG_MARGIN_X + 320, current_y), value, fill="black", font=text_font)
        current_y += 48

    return y + box_height + 30


def draw_image_footer(draw: ImageDraw.ImageDraw, text: str, fonts: tuple) -> None:
    _, _, text_font = fonts
    draw.text((IMG_MARGIN_X, IMG_HEIGHT - 70), text, fill=(107, 114, 128), font=text_font)


def save_image_as_pdf(path: Path, image: Image.Image) -> None:
    image_rgb = image.convert("RGB")
    image_rgb.save(path, "PDF", resolution=150.0)


def create_degraded_invoice_pdf(path: Path, supplier: dict, variant: str) -> None:
    fonts = get_fonts()
    image, draw = create_base_image()
    y = draw_image_header(draw, supplier, "FACTURE FOURNISSEUR", fonts)

    if variant == "blur":
        siret_label = "S1RET"
        date_label = "Date em1ssion"
        footer = "Simulation document flou / OCR bruite."
    else:
        siret_label = "SIRET"
        date_label = "Date d'emission"
        footer = "Simulation document mal capture / rotation."

    y = draw_image_section_title(draw, y, "Informations fournisseur", fonts)
    y = draw_image_box(draw, y, [
        ("Fournisseur", supplier["supplier_name"]),
        (siret_label, supplier["invoice_siret"]),
        ("TVA", supplier["tva"])
    ], fonts)

    y = draw_image_section_title(draw, y, "Informations de facturation", fonts)
    y = draw_image_box(draw, y, [
        (date_label, supplier["date_emission"]),
        ("Montant HT", f"{supplier['montant_ht']:.2f} EUR"),
        ("Montant TTC", f"{supplier['montant_ttc']:.2f} EUR")
    ], fonts)

    draw_image_footer(draw, footer, fonts)

    if variant == "blur":
        image = image.filter(ImageFilter.GaussianBlur(radius=2.8))
    elif variant == "rotate":
        image = image.rotate(4, expand=True, fillcolor="white")

    save_image_as_pdf(path, image)


# =========================
# GENERATION
# =========================

def generate_main_documents(suppliers: list[dict]) -> None:
    for supplier in suppliers:
        supplier_id = supplier["supplier_id"]
        scenario = supplier["scenario"]

        create_invoice_pdf(
            FACTURE_DIR / f"FAC_{supplier_id}_{scenario}.pdf",
            supplier
        )
        create_urssaf_pdf(
            URSSAF_DIR / f"URS_{supplier_id}_{scenario}.pdf",
            supplier
        )
        create_rib_pdf(
            RIB_DIR / f"RIB_{supplier_id}_{scenario}.pdf",
            supplier
        )


def generate_degraded_variants(suppliers: list[dict]) -> None:
    for supplier in suppliers:
        supplier_id = supplier["supplier_id"]
        scenario = supplier["scenario"]
        degraded_documents = supplier.get("degraded_documents", [])

        if "invoice_blur" in degraded_documents:
            create_degraded_invoice_pdf(
                DEGRADED_DIR / f"FAC_{supplier_id}_{scenario}_blur.pdf",
                supplier,
                "blur"
            )

        if "invoice_rotate" in degraded_documents:
            create_degraded_invoice_pdf(
                DEGRADED_DIR / f"FAC_{supplier_id}_{scenario}_rotate.pdf",
                supplier,
                "rotate"
            )


def main() -> None:
    ensure_directories()
    suppliers = load_suppliers()
    generate_main_documents(suppliers)
    generate_degraded_variants(suppliers)
    print("Dataset PDF généré avec succès.")


if __name__ == "__main__":
    main()