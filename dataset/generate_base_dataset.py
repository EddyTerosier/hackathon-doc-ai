import json
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


BASE_DIR = Path(__file__).resolve().parent
GROUND_TRUTH_DIR = BASE_DIR / "ground_truth"
RAW_DIR = BASE_DIR / "raw"

FACTURE_DIR = RAW_DIR / "facture"
URSSAF_DIR = RAW_DIR / "urssaf"
RIB_DIR = RAW_DIR / "rib"
DEGRADED_DIR = RAW_DIR / "degraded"

PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 50
TOP_MARGIN = 50
LINE_HEIGHT = 18


def ensure_directories() -> None:
    FACTURE_DIR.mkdir(parents=True, exist_ok=True)
    URSSAF_DIR.mkdir(parents=True, exist_ok=True)
    RIB_DIR.mkdir(parents=True, exist_ok=True)
    DEGRADED_DIR.mkdir(parents=True, exist_ok=True)


def load_suppliers() -> list[dict]:
    suppliers_path = GROUND_TRUTH_DIR / "suppliers.json"
    with suppliers_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def draw_header(pdf: canvas.Canvas, title: str, supplier_id: str, scenario: str) -> float:
    y = PAGE_HEIGHT - TOP_MARGIN
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(LEFT_MARGIN, y, title)

    y -= 28
    pdf.setFont("Helvetica", 11)
    pdf.drawString(LEFT_MARGIN, y, f"Reference dossier : {supplier_id}")
    y -= 16
    pdf.drawString(LEFT_MARGIN, y, f"Scenario : {scenario}")
    y -= 24
    return y


def draw_multiline(pdf: canvas.Canvas, lines: list[str], start_y: float) -> None:
    y = start_y
    pdf.setFont("Helvetica", 12)

    for line in lines:
        pdf.drawString(LEFT_MARGIN, y, line)
        y -= LINE_HEIGHT


def create_pdf(path: Path, title: str, supplier: dict, lines: list[str]) -> None:
    pdf = canvas.Canvas(str(path), pagesize=A4)
    y = draw_header(pdf, title, supplier["supplier_id"], supplier["scenario"])
    draw_multiline(pdf, lines, y)
    pdf.save()


def build_invoice_lines(supplier: dict) -> list[str]:
    return [
        f"Fournisseur : {supplier['supplier_name']}",
        f"SIRET : {supplier['invoice_siret']}",
        f"TVA intracommunautaire : {supplier['tva']}",
        f"Date d'emission : {supplier['date_emission']}",
        "",
        f"Montant HT : {supplier['montant_ht']:.2f} EUR",
        f"Montant TTC : {supplier['montant_ttc']:.2f} EUR",
        "",
        "Merci pour votre confiance."
    ]


def build_urssaf_lines(supplier: dict) -> list[str]:
    return [
        f"Entreprise : {supplier['supplier_name']}",
        f"SIRET : {supplier['urssaf_siret']}",
        f"Date d'expiration : {supplier['date_expiration']}",
        "",
        "Document attestant de la regularite de la situation sociale."
    ]


def build_rib_lines(supplier: dict) -> list[str]:
    bic_value = supplier["rib_bic"] if supplier["rib_bic"] else "NON RENSEIGNE"
    return [
        f"Titulaire du compte : {supplier['supplier_name']}",
        f"IBAN : {supplier['rib_iban']}",
        f"BIC : {bic_value}"
    ]


def generate_main_documents(suppliers: list[dict]) -> None:
    for supplier in suppliers:
        supplier_id = supplier["supplier_id"]
        scenario = supplier["scenario"]

        facture_path = FACTURE_DIR / f"FAC_{supplier_id}_{scenario}.pdf"
        urssaf_path = URSSAF_DIR / f"URS_{supplier_id}_{scenario}.pdf"
        rib_path = RIB_DIR / f"RIB_{supplier_id}_{scenario}.pdf"

        create_pdf(
            facture_path,
            "FACTURE FOURNISSEUR",
            supplier,
            build_invoice_lines(supplier)
        )

        create_pdf(
            urssaf_path,
            "ATTESTATION DE VIGILANCE URSSAF",
            supplier,
            build_urssaf_lines(supplier)
        )

        create_pdf(
            rib_path,
            "RELEVE D'IDENTITE BANCAIRE",
            supplier,
            build_rib_lines(supplier)
        )


def generate_degraded_variants(suppliers: list[dict]) -> None:
    for supplier in suppliers:
        supplier_id = supplier["supplier_id"]
        scenario = supplier["scenario"]
        degraded_documents = supplier.get("degraded_documents", [])

        if "invoice_blur" in degraded_documents:
            blur_path = DEGRADED_DIR / f"FAC_{supplier_id}_{scenario}_blur.pdf"
            blur_lines = [
                f"Fournisseur : {supplier['supplier_name']}",
                f"S1RET : {supplier['invoice_siret']}",
                f"TVA : {supplier['tva']}",
                f"Date em1ssion : {supplier['date_emission']}",
                "",
                f"Montant HT : {supplier['montant_ht']:.2f} EUR",
                f"Montant TTC : {supplier['montant_ttc']:.2f} EUR",
                "",
                "Document degrade - simulation OCR difficile"
            ]
            create_pdf(blur_path, "FACTURE FOURNISSEUR", supplier, blur_lines)

        if "invoice_rotate" in degraded_documents:
            rotate_path = DEGRADED_DIR / f"FAC_{supplier_id}_{scenario}_rotate.pdf"
            rotate_lines = [
                f"Fournisseur : {supplier['supplier_name']}",
                f"SIRET : {supplier['invoice_siret']}",
                f"TVA intracom : {supplier['tva']}",
                f"Date d'emission : {supplier['date_emission']}",
                "",
                f"Montant HT : {supplier['montant_ht']:.2f} EUR",
                f"Montant TTC : {supplier['montant_ttc']:.2f} EUR",
                "",
                "Document degrade - simulation document mal capture"
            ]
            create_pdf(rotate_path, "FACTURE FOURNISSEUR", supplier, rotate_lines)


def main() -> None:
    ensure_directories()
    suppliers = load_suppliers()
    generate_main_documents(suppliers)
    generate_degraded_variants(suppliers)
    print("Dataset PDF genere avec succes.")


if __name__ == "__main__":
    main()