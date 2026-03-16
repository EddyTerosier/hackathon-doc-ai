import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter


BASE_DIR = Path(__file__).resolve().parent
GROUND_TRUTH_DIR = BASE_DIR / "ground_truth"
RAW_IMAGES_DIR = BASE_DIR / "raw_images"

FACTURE_DIR = RAW_IMAGES_DIR / "facture"
URSSAF_DIR = RAW_IMAGES_DIR / "urssaf"
RIB_DIR = RAW_IMAGES_DIR / "rib"
DEGRADED_DIR = RAW_IMAGES_DIR / "degraded"

WIDTH = 1240
HEIGHT = 1754
MARGIN_X = 80
LINE_HEIGHT = 42


def ensure_directories() -> None:
    FACTURE_DIR.mkdir(parents=True, exist_ok=True)
    URSSAF_DIR.mkdir(parents=True, exist_ok=True)
    RIB_DIR.mkdir(parents=True, exist_ok=True)
    DEGRADED_DIR.mkdir(parents=True, exist_ok=True)


def load_suppliers() -> list[dict]:
    suppliers_path = GROUND_TRUTH_DIR / "suppliers.json"
    with suppliers_path.open("r", encoding="utf-8") as file:
        return json.load(file)


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
    image = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(image)
    return image, draw


def draw_header(draw: ImageDraw.ImageDraw, supplier: dict, title: str, fonts: tuple) -> int:
    title_font, subtitle_font, _ = fonts

    draw.rectangle([(0, 0), (WIDTH, 140)], fill=(31, 41, 55))
    draw.text((MARGIN_X, 35), title, fill="white", font=title_font)
    draw.text(
        (MARGIN_X, 90),
        f"Reference dossier : {supplier['supplier_id']} | Scenario : {supplier['scenario']}",
        fill="white",
        font=subtitle_font,
    )
    return 190


def draw_section_title(draw: ImageDraw.ImageDraw, y: int, title: str, fonts: tuple) -> int:
    _, subtitle_font, _ = fonts
    draw.text((MARGIN_X, y), title, fill=(17, 24, 39), font=subtitle_font)
    draw.line((MARGIN_X, y + 35, WIDTH - MARGIN_X, y + 35), fill=(209, 213, 219), width=2)
    return y + 55


def draw_box(draw: ImageDraw.ImageDraw, y: int, items: list[tuple[str, str]], fonts: tuple) -> int:
    _, _, text_font = fonts
    box_height = 30 + len(items) * 48
    draw.rounded_rectangle(
        [(MARGIN_X, y), (WIDTH - MARGIN_X, y + box_height)],
        radius=12,
        outline=(209, 213, 219),
        width=2,
        fill=(249, 250, 251),
    )

    current_y = y + 18
    for label, value in items:
        draw.text((MARGIN_X + 20, current_y), f"{label} :", fill=(55, 65, 81), font=text_font)
        draw.text((MARGIN_X + 320, current_y), value, fill="black", font=text_font)
        current_y += 48

    return y + box_height + 30


def draw_footer(draw: ImageDraw.ImageDraw, text: str, fonts: tuple) -> None:
    _, _, text_font = fonts
    draw.text((MARGIN_X, HEIGHT - 70), text, fill=(107, 114, 128), font=text_font)


def save_png(path: Path, image: Image.Image) -> None:
    image.save(path, format="PNG")


def build_invoice_image(path: Path, supplier: dict) -> None:
    fonts = get_fonts()
    image, draw = create_base_image()
    y = draw_header(draw, supplier, "FACTURE FOURNISSEUR", fonts)

    y = draw_section_title(draw, y, "Informations fournisseur", fonts)
    y = draw_box(draw, y, [
        ("Fournisseur", supplier["supplier_name"]),
        ("SIRET", supplier["invoice_siret"]),
        ("TVA intracommunautaire", supplier["tva"]),
    ], fonts)

    y = draw_section_title(draw, y, "Informations de facturation", fonts)
    y = draw_box(draw, y, [
        ("Date d'emission", supplier["date_emission"]),
        ("Montant HT", f"{supplier['montant_ht']:.2f} EUR"),
        ("Montant TTC", f"{supplier['montant_ttc']:.2f} EUR"),
    ], fonts)

    draw_footer(draw, "Document genere pour tests de traitement documentaire.", fonts)
    save_png(path, image)


def build_urssaf_image(path: Path, supplier: dict) -> None:
    fonts = get_fonts()
    image, draw = create_base_image()
    y = draw_header(draw, supplier, "ATTESTATION DE VIGILANCE URSSAF", fonts)

    y = draw_section_title(draw, y, "Informations entreprise", fonts)
    y = draw_box(draw, y, [
        ("Entreprise", supplier["supplier_name"]),
        ("SIRET", supplier["urssaf_siret"]),
        ("Date d'expiration", supplier["date_expiration"]),
    ], fonts)

    draw_footer(draw, "Document URSSAF fictif genere pour tests.", fonts)
    save_png(path, image)


def build_rib_image(path: Path, supplier: dict) -> None:
    fonts = get_fonts()
    image, draw = create_base_image()
    y = draw_header(draw, supplier, "RELEVE D'IDENTITE BANCAIRE", fonts)

    bic_value = supplier["rib_bic"] if supplier["rib_bic"] else "NON RENSEIGNE"

    y = draw_section_title(draw, y, "Informations bancaires", fonts)
    y = draw_box(draw, y, [
        ("Titulaire du compte", supplier["supplier_name"]),
        ("IBAN", supplier["rib_iban"]),
        ("BIC", bic_value),
    ], fonts)

    draw_footer(draw, "Document bancaire fictif genere pour tests.", fonts)
    save_png(path, image)


def build_degraded_invoice_image(path: Path, supplier: dict, variant: str) -> None:
    fonts = get_fonts()
    image, draw = create_base_image()
    y = draw_header(draw, supplier, "FACTURE FOURNISSEUR", fonts)

    if variant == "blur":
        siret_label = "S1RET"
        date_label = "Date em1ssion"
        footer = "Simulation document flou / OCR bruite."
    else:
        siret_label = "SIRET"
        date_label = "Date d'emission"
        footer = "Simulation document mal capture / rotation."

    y = draw_section_title(draw, y, "Informations fournisseur", fonts)
    y = draw_box(draw, y, [
        ("Fournisseur", supplier["supplier_name"]),
        (siret_label, supplier["invoice_siret"]),
        ("TVA", supplier["tva"]),
    ], fonts)

    y = draw_section_title(draw, y, "Informations de facturation", fonts)
    y = draw_box(draw, y, [
        (date_label, supplier["date_emission"]),
        ("Montant HT", f"{supplier['montant_ht']:.2f} EUR"),
        ("Montant TTC", f"{supplier['montant_ttc']:.2f} EUR"),
    ], fonts)

    draw_footer(draw, footer, fonts)

    if variant == "blur":
        image = image.filter(ImageFilter.GaussianBlur(radius=2.8))
    elif variant == "rotate":
        image = image.rotate(4, expand=True, fillcolor="white")

    save_png(path, image)


def generate_main_images(suppliers: list[dict]) -> None:
    for supplier in suppliers:
        supplier_id = supplier["supplier_id"]
        scenario = supplier["scenario"]

        build_invoice_image(FACTURE_DIR / f"FAC_{supplier_id}_{scenario}.png", supplier)
        build_urssaf_image(URSSAF_DIR / f"URS_{supplier_id}_{scenario}.png", supplier)
        build_rib_image(RIB_DIR / f"RIB_{supplier_id}_{scenario}.png", supplier)


def generate_degraded_images(suppliers: list[dict]) -> None:
    for supplier in suppliers:
        supplier_id = supplier["supplier_id"]
        scenario = supplier["scenario"]
        degraded_documents = supplier.get("degraded_documents", [])

        if "invoice_blur" in degraded_documents:
            build_degraded_invoice_image(
                DEGRADED_DIR / f"FAC_{supplier_id}_{scenario}_blur.png",
                supplier,
                "blur",
            )

        if "invoice_rotate" in degraded_documents:
            build_degraded_invoice_image(
                DEGRADED_DIR / f"FAC_{supplier_id}_{scenario}_rotate.png",
                supplier,
                "rotate",
            )


def main() -> None:
    ensure_directories()
    suppliers = load_suppliers()
    generate_main_images(suppliers)
    generate_degraded_images(suppliers)
    print("Images PNG generees avec succes.")


if __name__ == "__main__":
    main()