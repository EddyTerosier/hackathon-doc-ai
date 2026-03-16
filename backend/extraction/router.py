"""
Routeur FastAPI - Classification & Extraction
Personne 3 - Hackathon Doc AI
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .classifier import extract, ExtractionResult

router = APIRouter(prefix="/extraction", tags=["extraction"])


class ExtractRequest(BaseModel):
    text: str  # texte OCR brut


class ExtractResponse(BaseModel):
    document_type: str
    confidence: float
    champs: dict


@router.post("/", response_model=ExtractResponse)
def extract_document(req: ExtractRequest) -> ExtractResponse:
    """
    Classifie et extrait les champs structurés d'un texte OCR.

    Retourne :
    - document_type : facture | attestation_urssaf | rib | inconnu
    - confidence    : score entre 0 et 1
    - champs        : SIRET, TVA, IBAN, BIC, dates, montants, etc.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Le texte OCR est vide.")

    result: ExtractionResult = extract(req.text)
    return ExtractResponse(**result.to_dict())