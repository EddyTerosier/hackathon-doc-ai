"""
Tests unitaires - Classification & Extraction
Personne 3 - Hackathon Doc AI
"""

import pytest
from backend.extraction.classifier import (
    classify,
    extract,
    DocumentType,
)

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