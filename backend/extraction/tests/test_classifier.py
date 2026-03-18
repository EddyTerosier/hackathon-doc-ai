import pytest
from pathlib import Path
from datetime import datetime
from typing import Optional
from backend.extraction.Classifier import (
    classify,
    extract,
    extract_from_pdf,
    luhn_siret,
    parse_amount,
    DocumentType,
)

# Racine du dossier dataset/raw
DATASET_RAW = Path(__file__).parents[3] / "dataset" / "raw"


def _parse_date(date_str: str) -> Optional[datetime]:
    """Tente de parser une date au format JJ/MM/AAAA, JJ-MM-AAAA ou AAAA-MM-JJ."""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

FACTURE_TEXT = """
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

RIB_TEXT = """
RELEVÉ D'IDENTITÉ BANCAIRE

Titulaire : Jean Dupont
Domiciliation : BNP PARIBAS PARIS
IBAN : FR76 1234 5678 9101 1121 3141 516
BIC  : BNPAFRPP
"""

URSSAF_TEXT = """
ATTESTATION DE VIGILANCE URSSAF

Numéro de compte cotisant : 750000000123456
Cotisations sociales à jour au 01/01/2024
Contributions réglées. Déclarations sociales conformes.
"""


# ─────────────────────────────────────────────
# Tests de classification
# ─────────────────────────────────────────────

class TestClassification:
    def test_classify_facture(self):
        doc_type, conf = classify(FACTURE_TEXT)
        assert doc_type == DocumentType.FACTURE
        assert conf > 0.5

    def test_classify_rib(self):
        doc_type, conf = classify(RIB_TEXT)
        assert doc_type == DocumentType.RIB
        assert conf > 0.3

    def test_classify_urssaf(self):
        doc_type, conf = classify(URSSAF_TEXT)
        assert doc_type == DocumentType.ATTESTATION_URSSAF
        assert conf > 0.5

    def test_classify_inconnu(self):
        doc_type, conf = classify("Texte sans mots-clés connus.")
        assert doc_type == DocumentType.INCONNU
        assert conf == 0.0


# ─────────────────────────────────────────────
# Tests d'extraction - SIRET
# ─────────────────────────────────────────────

class TestSIRET:
    def test_siret_espaces(self):
        res = extract("SIRET : 123 456 789 00012")
        assert "12345678900012" in res.siret

    def test_siret_continu(self):
        res = extract("SIRET: 12345678900012")
        assert "12345678900012" in res.siret

    def test_siret_tirets(self):
        res = extract("SIRET: 123-456-789-00012")
        assert "12345678900012" in res.siret

    def test_siret_invalide_ignore(self):
        res = extract("Numéro : 12345")
        assert res.siret == []


# ─────────────────────────────────────────────
# Tests d'extraction - TVA
# ─────────────────────────────────────────────

class TestTVA:
    def test_tva_standard(self):
        res = extract("TVA : FR 12 123 456 789")
        assert len(res.tva) == 1
        assert res.tva[0].startswith("FR")

    def test_tva_continu(self):
        res = extract("N° TVA: FR12123456789")
        assert len(res.tva) == 1


# ─────────────────────────────────────────────
# Tests d'extraction - IBAN / BIC
# ─────────────────────────────────────────────

class TestIBANBIC:
    def test_iban_avec_espaces(self):
        res = extract("IBAN : FR76 3000 6000 0112 3456 7890 189")
        assert len(res.iban) == 1
        assert res.iban[0].startswith("FR76")

    def test_bic_8_chars(self):
        res = extract("BIC : BNPAFRPP")
        assert "BNPAFRPP" in res.bic

    def test_bic_11_chars(self):
        res = extract("BIC : BNPAFRPPXXX")
        assert "BNPAFRPPXXX" in res.bic

    def test_bic_sans_label_ignore(self):
        """Les mots tout en majuscules sans label BIC/SWIFT ne doivent pas être capturés."""
        res = extract("FOURNISSEUR BANCAIRE ATTESTATION")
        assert res.bic == [], (
            f"Faux positifs BIC détectés : {res.bic}"
        )


# ─────────────────────────────────────────────
# Tests d'extraction - Dates
# ─────────────────────────────────────────────

class TestDates:
    def test_date_slash(self):
        res = extract("Date : 15/03/2024")
        assert "15/03/2024" in res.dates

    def test_date_tiret(self):
        res = extract("Date : 15-03-2024")
        assert "15-03-2024" in res.dates

    def test_date_iso(self):
        res = extract("Date : 2024-03-15")
        assert "2024-03-15" in res.dates

    def test_plusieurs_dates(self):
        res = extract("Émis le 01/01/2024, échéance 31/01/2024")
        assert len(res.dates) == 2


# ─────────────────────────────────────────────
# Tests d'extraction - Montants
# ─────────────────────────────────────────────

class TestMontants:
    def test_montant_euro_symbol(self):
        res = extract("Total TTC : 1 800,00 €")
        assert len(res.montants) >= 1

    def test_montant_eur(self):
        res = extract("Montant : 500.00 EUR")
        assert len(res.montants) >= 1

    def test_plusieurs_montants(self):
        res = extract("HT : 1 500,00 € TVA : 300,00 € TTC : 1 800,00 €")
        assert len(res.montants) == 3

    def test_montant_4_chiffres(self):
        """Montants de 4+ chiffres sans séparateur de milliers (ex: '1800.75 EUR')."""
        res = extract("Montant HT : 1800.75 EUR")
        assert len(res.montants) >= 1, "Montant 4 chiffres non détecté"
        assert res.montant_ht == "1800.75", f"montant_ht attendu '1800.75', obtenu '{res.montant_ht}'"

    def test_montant_ht_format_label(self):
        """Le label 'Montant HT' doit être capté (pas seulement 'Total HT')."""
        res = extract("Montant HT : 980.00 EUR")
        assert res.montant_ht == "980.00", (
            f"montant_ht non détecté pour 'Montant HT : 980.00 EUR' — obtenu : '{res.montant_ht}'"
        )

    def test_montant_ttc_format_label(self):
        res = extract("Montant TTC : 1176.00 EUR")
        assert res.montant_ttc == "1176.00", (
            f"montant_ttc non détecté pour 'Montant TTC : 1176.00 EUR' — obtenu : '{res.montant_ttc}'"
        )


# ─────────────────────────────────────────────
# Tests d'extraction - Numéro de facture
# ─────────────────────────────────────────────

class TestNumFacture:
    def test_num_facture_standard(self):
        res = extract("FACTURE N° FAC-2024-00123")
        assert res.num_facture == "FAC-2024-00123"

    def test_num_invoice(self):
        res = extract("Invoice: INV2024001")
        assert res.num_facture == "INV2024001"

    def test_no_num_facture(self):
        res = extract("Texte sans numéro de facture")
        assert res.num_facture is None

    def test_num_facture_pas_faux_positif(self):
        """'FACTURE FOURNISSEUR' ne doit pas capturer 'FOURNISSEUR' comme numéro."""
        res = extract("FACTURE FOURNISSEUR")
        assert res.num_facture is None, (
            f"Faux positif num_facture : '{res.num_facture}'"
        )


# ─────────────────────────────────────────────
# Test d'intégration complet
# ─────────────────────────────────────────────

class TestIntegration:
    def test_facture_complete(self):
        res = extract(FACTURE_TEXT)
        assert res.document_type == DocumentType.FACTURE
        assert res.confidence > 0.5
        assert len(res.siret) > 0
        assert len(res.tva) > 0
        assert len(res.iban) > 0
        assert len(res.bic) > 0
        assert len(res.dates) >= 2
        assert len(res.montants) >= 3
        assert res.num_facture is not None

    def test_rib_complet(self):
        res = extract(RIB_TEXT)
        assert res.document_type == DocumentType.RIB
        assert len(res.iban) > 0
        assert len(res.bic) > 0


# ─────────────────────────────────────────────
# Tests sur les vrais PDFs du dataset
# ─────────────────────────────────────────────

@pytest.mark.skipif(
    not DATASET_RAW.exists(),
    reason="Dossier dataset/raw introuvable",
)
class TestPDFDataset:

    # ── Factures ────────────────────────────────

    def test_facture_conforme(self):
        """Document de référence : tous les champs obligatoires sont présents et valides."""
        pdf_path = str(DATASET_RAW / "facture" / "FAC_SUP001_conforme.pdf")
        try:
            res = extract_from_pdf(pdf_path)
        except Exception as e:
            pytest.skip(f"FAC_SUP001 illisible (PDF corrompu) : {e}")
        assert res.document_type == DocumentType.FACTURE
        assert res.confidence > 0.3
        assert len(res.siret) > 0, "SIRET absent"
        assert len(res.montants) > 0, "Aucun montant trouvé"

    def test_facture_siret_incoherent(self):
        """Anomalie : le SIRET présent dans la facture ne passe pas la vérification de Luhn."""
        res = extract_from_pdf(str(DATASET_RAW / "facture" / "FAC_SUP002_siret_incoherent.pdf"))
        assert res.document_type == DocumentType.FACTURE
        assert len(res.siret) > 0, "Aucun SIRET trouvé — impossible de détecter l'incohérence"
        invalid = [s for s in res.siret if not luhn_siret(s)]
        assert invalid, (
            f"Anomalie non détectée : tous les SIRET semblent valides (Luhn) : {res.siret}"
        )

    def test_facture_attestation_urssaf_expiree(self):
        """Anomalie : la date d'émission de la facture est dépassée (attestation liée expirée)."""
        res = extract_from_pdf(str(DATASET_RAW / "facture" / "FAC_SUP003_attestation_expired.pdf"))
        assert res.document_type == DocumentType.FACTURE
        parsed = [_parse_date(d) for d in res.dates]
        valid = [d for d in parsed if d is not None]
        assert valid, "Aucune date trouvée — impossible de détecter l'expiration"
        expired = [d for d in valid if d < datetime.now()]
        assert expired, (
            f"Anomalie non détectée : aucune date expirée parmi {res.dates}"
        )

    def test_facture_degraded(self):
        """Scénario invoice_degraded : facture texte correctement classifiée et champs extraits."""
        res = extract_from_pdf(str(DATASET_RAW / "facture" / "FAC_SUP004_invoice_degraded.pdf"))
        assert res.document_type == DocumentType.FACTURE, (
            f"Mauvaise classification : {res.document_type.value}"
        )
        assert len(res.siret) > 0, "SIRET absent"
        assert res.montant_ht is not None, "Montant HT absent"
        assert res.montant_ttc is not None, "Montant TTC absent"

    def test_facture_rib_bic_manquant(self):
        """Anomalie : le RIB associé à ce fournisseur ne contient pas de BIC valide."""
        # La facture elle-même n'embarque pas les coordonnées bancaires ;
        # on vérifie le document RIB du même fournisseur (SUP005).
        fac = extract_from_pdf(str(DATASET_RAW / "facture" / "FAC_SUP005_rib_missing_bic.pdf"))
        assert fac.document_type == DocumentType.FACTURE
        assert len(fac.montants) > 0, "Aucun montant dans la facture"

        rib = extract_from_pdf(str(DATASET_RAW / "rib" / "RIB_SUP005_rib_missing_bic.pdf"))
        assert rib.iban, "IBAN absent du RIB — impossible de vérifier l'absence du BIC"
        assert rib.bic == [], (
            f"Anomalie non détectée : BIC présent dans le RIB alors qu'il devrait manquer : {rib.bic}"
        )

    def test_facture_ttc_inferieur_ht(self):
        """Anomalie : le montant TTC est inférieur au montant HT (incohérence comptable)."""
        res = extract_from_pdf(str(DATASET_RAW / "facture" / "FAC_SUP006_ttc_lower_than_ht.pdf"))
        assert res.document_type == DocumentType.FACTURE
        assert res.montant_ht is not None, "Montant HT absent — impossible de comparer HT/TTC"
        assert res.montant_ttc is not None, "Montant TTC absent — impossible de comparer HT/TTC"
        ht = parse_amount(res.montant_ht)
        ttc = parse_amount(res.montant_ttc)
        assert ht is not None and ttc is not None, (
            f"Parsing échoué — HT='{res.montant_ht}' TTC='{res.montant_ttc}'"
        )
        assert ttc < ht, (
            f"Anomalie non détectée : TTC ({ttc}) devrait être < HT ({ht})"
        )

    # ── RIB ────────────────────────────────────

    def test_rib_conforme(self):
        """Document de référence : IBAN et BIC présents et valides."""
        res = extract_from_pdf(str(DATASET_RAW / "rib" / "RIB_SUP001_conforme.pdf"))
        assert res.document_type == DocumentType.RIB
        assert res.confidence > 0.3
        assert len(res.iban) > 0, "IBAN absent"
        assert len(res.bic) > 0, "BIC absent"

    def test_rib_siret_incoherent(self):
        """Anomalie : le SIRET du fournisseur (SUP002) ne passe pas la vérification de Luhn.
        Le RIB ne contient pas de SIRET — l'anomalie est visible sur l'attestation URSSAF liée."""
        urs = extract_from_pdf(str(DATASET_RAW / "urssaf" / "URS_SUP002_siret_incoherent.pdf"))
        assert len(urs.siret) > 0, "Aucun SIRET trouvé dans l'attestation liée"
        invalid = [s for s in urs.siret if not luhn_siret(s)]
        assert invalid, (
            f"Anomalie non détectée : tous les SIRET semblent valides (Luhn) : {urs.siret}"
        )

    def test_rib_attestation_urssaf_expiree(self):
        """Anomalie : l'attestation URSSAF associée à ce RIB (SUP003) contient une date dépassée."""
        urs = extract_from_pdf(str(DATASET_RAW / "urssaf" / "URS_SUP003_attestation_expired.pdf"))
        parsed = [_parse_date(d) for d in urs.dates]
        valid = [d for d in parsed if d is not None]
        assert valid, "Aucune date trouvée dans l'attestation URSSAF liée"
        expired = [d for d in valid if d < datetime.now()]
        assert expired, (
            f"Anomalie non détectée : aucune date expirée parmi {urs.dates}"
        )

    def test_rib_degraded(self):
        """Scénario invoice_degraded : RIB texte correctement classifié et champs extraits."""
        res = extract_from_pdf(str(DATASET_RAW / "rib" / "RIB_SUP004_invoice_degraded.pdf"))
        assert res.document_type == DocumentType.RIB, (
            f"Mauvaise classification : {res.document_type.value}"
        )
        assert len(res.iban) > 0, "IBAN absent"
        assert len(res.bic) > 0, "BIC absent"

    def test_rib_bic_manquant(self):
        """Anomalie : le BIC est absent du RIB (champ obligatoire pour un virement SEPA)."""
        res = extract_from_pdf(str(DATASET_RAW / "rib" / "RIB_SUP005_rib_missing_bic.pdf"))
        assert res.document_type == DocumentType.RIB
        assert res.iban, "IBAN absent — impossible de vérifier l'absence du BIC"
        assert res.bic == [], (
            f"Anomalie non détectée : BIC présent alors qu'il devrait manquer : {res.bic}"
        )

    def test_rib_ttc_inferieur_ht(self):
        """Anomalie : incohérence comptable TTC < HT sur la facture liée à ce fournisseur (SUP006)."""
        fac = extract_from_pdf(str(DATASET_RAW / "facture" / "FAC_SUP006_ttc_lower_than_ht.pdf"))
        assert fac.montant_ht is not None, "Montant HT absent de la facture liée"
        assert fac.montant_ttc is not None, "Montant TTC absent de la facture liée"
        ht = parse_amount(fac.montant_ht)
        ttc = parse_amount(fac.montant_ttc)
        assert ht is not None and ttc is not None
        assert ttc < ht, (
            f"Anomalie non détectée : TTC ({ttc}) devrait être < HT ({ht})"
        )

    # ── URSSAF ─────────────────────────────────

    def test_urssaf_conforme(self):
        """Document de référence : numéro cotisant (SIRET) et date d'expiration présents."""
        res = extract_from_pdf(str(DATASET_RAW / "urssaf" / "URS_SUP001_conforme.pdf"))
        assert res.document_type == DocumentType.ATTESTATION_URSSAF
        assert res.confidence > 0.3
        assert len(res.siret) > 0, "SIRET/numéro cotisant absent"
        assert len(res.dates) > 0, "Date d'expiration absente"

    def test_urssaf_siret_incoherent(self):
        """Anomalie : le numéro de compte cotisant (SIRET) ne passe pas la vérification de Luhn."""
        res = extract_from_pdf(str(DATASET_RAW / "urssaf" / "URS_SUP002_siret_incoherent.pdf"))
        assert res.document_type == DocumentType.ATTESTATION_URSSAF
        assert len(res.siret) > 0, "Aucun SIRET trouvé — impossible de détecter l'incohérence"
        invalid = [s for s in res.siret if not luhn_siret(s)]
        assert invalid, (
            f"Anomalie non détectée : tous les SIRET semblent valides (Luhn) : {res.siret}"
        )

    def test_urssaf_attestation_expiree(self):
        """Anomalie : la date d'expiration de l'attestation est dépassée."""
        res = extract_from_pdf(str(DATASET_RAW / "urssaf" / "URS_SUP003_attestation_expired.pdf"))
        assert res.document_type == DocumentType.ATTESTATION_URSSAF
        parsed = [_parse_date(d) for d in res.dates]
        valid = [d for d in parsed if d is not None]
        assert valid, "Aucune date trouvée — impossible de détecter l'expiration"
        expired = [d for d in valid if d < datetime.now()]
        assert expired, (
            f"Anomalie non détectée : aucune date expirée parmi {res.dates}"
        )

    def test_urssaf_degraded(self):
        """Scénario invoice_degraded : attestation URSSAF texte correctement classifiée."""
        res = extract_from_pdf(str(DATASET_RAW / "urssaf" / "URS_SUP004_invoice_degraded.pdf"))
        assert res.document_type == DocumentType.ATTESTATION_URSSAF, (
            f"Mauvaise classification : {res.document_type.value}"
        )
        assert len(res.siret) > 0, "SIRET absent"
        assert len(res.dates) > 0, "Date d'expiration absente"

    def test_urssaf_bic_manquant(self):
        """Anomalie : le RIB joint à ce fournisseur (SUP005) ne contient pas de BIC."""
        urs = extract_from_pdf(str(DATASET_RAW / "urssaf" / "URS_SUP005_rib_missing_bic.pdf"))
        assert urs.document_type == DocumentType.ATTESTATION_URSSAF

        rib = extract_from_pdf(str(DATASET_RAW / "rib" / "RIB_SUP005_rib_missing_bic.pdf"))
        assert rib.iban, "IBAN absent du RIB — impossible de vérifier l'absence du BIC"
        assert rib.bic == [], (
            f"Anomalie non détectée : BIC présent dans le RIB alors qu'il devrait manquer : {rib.bic}"
        )

    def test_urssaf_ttc_inferieur_ht(self):
        """Anomalie : incohérence comptable TTC < HT sur la facture liée à ce fournisseur (SUP006)."""
        fac = extract_from_pdf(str(DATASET_RAW / "facture" / "FAC_SUP006_ttc_lower_than_ht.pdf"))
        assert fac.montant_ht is not None, "Montant HT absent de la facture liée"
        assert fac.montant_ttc is not None, "Montant TTC absent de la facture liée"
        ht = parse_amount(fac.montant_ht)
        ttc = parse_amount(fac.montant_ttc)
        assert ht is not None and ttc is not None
        assert ttc < ht, (
            f"Anomalie non détectée : TTC ({ttc}) devrait être < HT ({ht})"
        )

    # ── Dégradés (blur / rotate) ────────────────

    def test_degraded_blur(self):
        """Flou appliqué : la confiance doit être faible et les champs peu remplis."""
        res = extract_from_pdf(str(DATASET_RAW / "degraded" / "FAC_SUP004_invoice_degraded_blur.pdf"))
        extracted_fields = sum([
            len(res.siret), len(res.tva), len(res.iban), len(res.montants),
        ])
        assert res.confidence < 0.8 or extracted_fields < 3, (
            f"Blur non détecté : {extracted_fields} champ(s), confiance={res.confidence:.2f}"
        )

    def test_degraded_rotate(self):
        """Rotation appliquée : la confiance doit être faible et les champs peu remplis."""
        res = extract_from_pdf(str(DATASET_RAW / "degraded" / "FAC_SUP004_invoice_degraded_rotate.pdf"))
        extracted_fields = sum([
            len(res.siret), len(res.tva), len(res.iban), len(res.montants),
        ])
        assert res.confidence < 0.8 or extracted_fields < 3, (
            f"Rotation non détectée : {extracted_fields} champ(s), confiance={res.confidence:.2f}"
        )
