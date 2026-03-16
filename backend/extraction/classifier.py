import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


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

    # BIC/SWIFT : 8 ou 11 caractères
    "bic": re.compile(
        r"\b([A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b"
    ),

    # Dates : JJ/MM/AAAA, JJ-MM-AAAA, JJ.MM.AAAA, AAAA-MM-JJ
    "date": re.compile(
        r"\b(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4}|\d{4}[\/\-\.]\d{2}[\/\-\.]\d{2})\b"
    ),

    # Montants : nombre avec séparateur décimal + € ou EUR
    "montant": re.compile(
        r"\b(\d{1,3}(?:[\s\.\,]\d{3})*(?:[,\.]\d{2})?)\s*(?:€|EUR|euros?)\b",
        re.IGNORECASE,
    ),

    # Numéro de facture
    "num_facture": re.compile(
        r"(?:facture|invoice|fact\.?|n°|no\.?)\s*[:#\-]?\s*([A-Z0-9\-\/]{4,20})",
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

    # BIC
    bic_matches = PATTERNS["bic"].findall(text)
    # Filtrer les faux positifs (mots communs tout en majuscules)
    STOPWORDS = {"TOTAL", "IBAN", "SIRET", "SIREN", "URSSAF", "EURO", "DATE"}
    result.bic = _clean([m for m in bic_matches if m not in STOPWORDS])

    # Dates
    result.dates = _clean(PATTERNS["date"].findall(text))

    # Montants
    montant_matches = PATTERNS["montant"].findall(text)
    result.montants = _clean(montant_matches)

    # Numéro de facture
    num_match = PATTERNS["num_facture"].search(text)
    if num_match:
        result.num_facture = num_match.group(1).strip()

    return result


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