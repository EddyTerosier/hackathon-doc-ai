import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import pdfplumber


# ─────────────────────────────────────────────
# Types de documents
# ─────────────────────────────────────────────

class DocumentType(str, Enum):
    FACTURE = "facture"
    ATTESTATION_URSSAF = "attestation_urssaf"
    RIB = "rib"
    INCONNU = "inconnu"


# ─────────────────────────────────────────────
# Patterns regex
# ─────────────────────────────────────────────

PATTERNS = {
    # SIRET : 14 chiffres (espaces tolérés tous les 3)
    "siret": re.compile(
        r"\b(\d{3}[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{5})\b"
    ),

    # SIREN : 9 chiffres
    "siren": re.compile(
        r"\b(\d{3}[\s\-]?\d{3}[\s\-]?\d{3})\b"
    ),

    # TVA intracommunautaire : FR + 2 caractères + 9 chiffres
    "tva": re.compile(
        r"\bFR[\s]?([A-Z0-9]{2})[\s]?(\d{3}[\s]?\d{3}[\s]?\d{3})\b",
        re.IGNORECASE,
    ),

    # IBAN français : FR76 + groupes de 4
    "iban": re.compile(
        r"\b(FR\d{2}[\s]?(?:\d{4}[\s]?){5}\d{3})\b",
        re.IGNORECASE,
    ),

    # BIC/SWIFT : 8 ou 11 caractères — nécessite le label BIC/SWIFT pour éviter les faux positifs
    "bic": re.compile(
        r"(?:BIC|SWIFT)\s*[:/]?\s*([A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b",
        re.IGNORECASE,
    ),

    # Dates : JJ/MM/AAAA, JJ-MM-AAAA, JJ.MM.AAAA, AAAA-MM-JJ
    "date": re.compile(
        r"\b(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4}|\d{4}[\/\-\.]\d{2}[\/\-\.]\d{2})\b"
    ),

    # Montants : nombre avec séparateur décimal + € ou EUR
    # Supporte : "1 500,00 €", "500.00 EUR", "1800.75 EUR" (4+ chiffres sans séparateur de milliers)
    # Note : pas de \b final car € n'est pas un caractère de mot
    "montant": re.compile(
        r"\b(\d{1,3}(?:[\s\.\,]\d{3})*(?:[,\.]\d{1,2})?|\d{4,}(?:[,\.]\d{1,2})?)\s*(?:€|EUR|euros?)(?!\w)",
        re.IGNORECASE,
    ),

    # Numéro de facture
    "num_facture": re.compile(
        r"(?:facture|invoice|fact\.?|n°|no\.?)\s*[:#\-]?\s*([A-Z0-9\-\/]{4,20})",
        re.IGNORECASE,
    ),

    # Montant HT (labelisé) — supporte "Montant HT : 1200.50 EUR", "Total HT : 1 500,00 €"
    "montant_ht": re.compile(
        r"(?:(?:montant|total)\s+)?H\.?T\.?\s*[:\-]?\s*(\d{1,3}(?:[\s\.\,]\d{3})*(?:[,\.]\d{1,2})?|\d{4,}(?:[,\.]\d{1,2})?)\s*(?:€|EUR)",
        re.IGNORECASE,
    ),

    # Montant TTC (labelisé) — supporte "Montant TTC : 1440.60 EUR", "Total TTC : 1 800,00 €"
    "montant_ttc": re.compile(
        r"(?:(?:montant|total)\s+)?T\.?T\.?C\.?\s*[:\-]?\s*(\d{1,3}(?:[\s\.\,]\d{3})*(?:[,\.]\d{1,2})?|\d{4,}(?:[,\.]\d{1,2})?)\s*(?:€|EUR)",
        re.IGNORECASE,
    ),
}

# ─────────────────────────────────────────────
# Mots-clés de classification
# ─────────────────────────────────────────────

KEYWORDS = {
    DocumentType.FACTURE: [
        "facture", "invoice", "total ttc", "total ht", "tva", "montant dû",
        "règlement", "échéance", "bon de commande", "prestation", "quantité",
        "prix unitaire", "remise",
    ],
    DocumentType.ATTESTATION_URSSAF: [
        "urssaf", "cotisations sociales", "attestation de vigilance",
        "contributions", "recouvrement", "régularité", "déclarations sociales",
        "numéro de compte cotisant",
    ],
    DocumentType.RIB: [
        "rib", "relevé d'identité bancaire", "iban", "bic", "swift",
        "domiciliation", "titulaire du compte", "établissement", "guichet",
        "numéro de compte",
    ],
}


# ─────────────────────────────────────────────
# Résultat d'extraction
# ─────────────────────────────────────────────

@dataclass
class ExtractionResult:
    document_type: DocumentType = DocumentType.INCONNU
    confidence: float = 0.0
    siret: list[str] = field(default_factory=list)
    siren: list[str] = field(default_factory=list)
    tva: list[str] = field(default_factory=list)
    iban: list[str] = field(default_factory=list)
    bic: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    montants: list[str] = field(default_factory=list)
    montant_ht: Optional[str] = None
    montant_ttc: Optional[str] = None
    num_facture: Optional[str] = None
    raw_matches: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "document_type": self.document_type.value,
            "confidence": round(self.confidence, 2),
            "champs": {
                "siret": self.siret,
                "siren": self.siren,
                "tva": self.tva,
                "iban": self.iban,
                "bic": self.bic,
                "dates": self.dates,
                "montants": self.montants,
                "montant_ht": self.montant_ht,
                "montant_ttc": self.montant_ttc,
                "num_facture": self.num_facture,
            },
        }


# ─────────────────────────────────────────────
# Classificateur
# ─────────────────────────────────────────────

def classify(text: str) -> tuple[DocumentType, float]:
    """
    Classe un document selon ses mots-clés.
    Retourne le type et un score de confiance [0, 1].
    """
    text_lower = text.lower()
    scores: dict[DocumentType, int] = {dt: 0 for dt in DocumentType}

    for doc_type, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[doc_type] += 1

    best_type = max(scores, key=lambda dt: scores[dt])
    best_score = scores[best_type]

    if best_score == 0:
        return DocumentType.INCONNU, 0.0

    total = sum(scores.values())
    confidence = best_score / total if total > 0 else 0.0
    # Bonus si au moins 2 mots-clés trouvés
    if best_score >= 2:
        confidence = min(confidence * 1.2, 1.0)

    return best_type, confidence


# ─────────────────────────────────────────────
# Extracteur
# ─────────────────────────────────────────────

def _clean(matches: list[str]) -> list[str]:
    """Déduplique et nettoie les correspondances."""
    seen = set()
    result = []
    for m in matches:
        cleaned = re.sub(r"\s+", " ", m).strip()
        if cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def extract(text: str) -> ExtractionResult:
    """
    Extrait tous les champs structurés d'un texte OCR.
    """
    result = ExtractionResult()

    # Classification
    result.document_type, result.confidence = classify(text)

    # SIRET (14 chiffres normalisés)
    siret_matches = PATTERNS["siret"].findall(text)
    result.siret = _clean([m.replace(" ", "").replace("-", "") for m in siret_matches
                           if len(re.sub(r"\D", "", m)) == 14])

    # SIREN (9 chiffres) — exclure ceux déjà dans un SIRET
    siren_raw = PATTERNS["siren"].findall(text)
    all_sirets_digits = [s.replace(" ", "") for s in result.siret]
    result.siren = _clean([
        m.replace(" ", "").replace("-", "")
        for m in siren_raw
        if len(re.sub(r"\D", "", m)) == 9
        and not any(s.startswith(m.replace(" ", "")) for s in all_sirets_digits)
    ])

    # TVA
    tva_matches = PATTERNS["tva"].findall(text)
    result.tva = _clean(["FR" + a + b for a, b in tva_matches])

    # IBAN
    iban_matches = PATTERNS["iban"].findall(text)
    result.iban = _clean([re.sub(r"\s", "", m).upper() for m in iban_matches])

    # BIC — le regex exige déjà le label BIC/SWIFT, on normalise en majuscules
    bic_matches = PATTERNS["bic"].findall(text)
    result.bic = _clean([m.upper() for m in bic_matches])

    # Dates
    result.dates = _clean(PATTERNS["date"].findall(text))

    # Montants
    montant_matches = PATTERNS["montant"].findall(text)
    result.montants = _clean(montant_matches)

    # Montant HT / TTC (labelisés)
    ht_match = PATTERNS["montant_ht"].search(text)
    if ht_match:
        result.montant_ht = ht_match.group(1).strip()
    ttc_match = PATTERNS["montant_ttc"].search(text)
    if ttc_match:
        result.montant_ttc = ttc_match.group(1).strip()

    # Numéro de facture — doit contenir au moins un chiffre (évite "FOURNISSEUR" etc.)
    for num_match in PATTERNS["num_facture"].finditer(text):
        candidate = num_match.group(1).strip()
        if re.search(r'\d', candidate):
            result.num_facture = candidate
            break

    return result


# ─────────────────────────────────────────────
# Validation métier
# ─────────────────────────────────────────────

def luhn_siret(siret: str) -> bool:
    """Vérifie la clé de Luhn d'un SIRET (14 chiffres normalisés)."""
    digits = re.sub(r"\D", "", siret)
    if len(digits) != 14:
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def parse_amount(amount_str: str) -> Optional[float]:
    """Convertit une chaîne de montant en float (ex: '1 500,00' → 1500.0)."""
    if not amount_str:
        return None
    cleaned = re.sub(r"[\s\u00a0]", "", amount_str)   # espaces insécables
    cleaned = cleaned.replace(",", ".")
    # supprime les séparateurs de milliers si plusieurs points
    parts = cleaned.split(".")
    if len(parts) > 2:
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(cleaned)
    except ValueError:
        return None


# ─────────────────────────────────────────────
# Lecture PDF
# ─────────────────────────────────────────────

def pdf_to_text(path: str) -> str:
    """Extrait le texte brut d'un PDF via pdfplumber."""
    parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                parts.append(page_text)
    return "\n".join(parts)


def extract_from_pdf(path: str) -> ExtractionResult:
    """Extrait les champs structurés directement depuis un fichier PDF."""
    return extract(pdf_to_text(path))


# ─────────────────────────────────────────────
# Point d'entrée principal (test rapide)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    sample_facture = """
    FACTURE N° FAC-2024-00123
    Date : 15/03/2024   Échéance : 15/04/2024

    Émetteur : ACME SAS
    SIRET : 123 456 789 00012
    TVA intracommunautaire : FR 12 123 456 789

    Prestation de conseil - 10h x 150 €
    Total HT : 1 500,00 €
    TVA 20% : 300,00 €
    Total TTC : 1 800,00 €

    Règlement par virement :
    IBAN : FR76 3000 6000 0112 3456 7890 189
    BIC  : BNPAFRPPXXX
    """

    sample_rib = """
    RELEVÉ D'IDENTITÉ BANCAIRE

    Titulaire : Jean Dupont
    Domiciliation : BNP PARIBAS PARIS
    IBAN : FR76 1234 5678 9101 1121 3141 516
    BIC  : BNPAFRPP
    """

    for label, sample in [("Facture", sample_facture), ("RIB", sample_rib)]:
        res = extract(sample)
        print(f"\n{'='*50}")
        print(f"  {label}")
        print(f"{'='*50}")
        import json
        print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False))