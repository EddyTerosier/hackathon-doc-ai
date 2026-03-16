# Hackathon Doc AI

Plateforme locale de traitement documentaire intelligent.

## Objectif

Permettre l'analyse automatique de documents administratifs :
- factures
- attestations URSSAF
- RIB

Fonctionnalités prévues :
- upload de documents
- OCR
- classification automatique
- extraction des champs clés
- validation de cohérence
- stockage MongoDB
- interface React
- exécution locale avec Docker

## Stack technique

- Frontend : React + Vite
- Backend : FastAPI
- Base de données : MongoDB
- OCR : Tesseract
- Conteneurisation : Docker Compose

## Périmètre V1

Documents pris en charge :
- facture
- attestation URSSAF
- RIB

## Structure du projet

- `backend/` : API et pipeline documentaire
- `frontend/` : interface utilisateur
- `dataset/` : documents de test
- `docs/` : documentation projet

## Lancement

À compléter.