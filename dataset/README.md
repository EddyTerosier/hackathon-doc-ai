# Dataset Hackathon Doc AI

## Objectif

Ce dossier contient le jeu de données de test du projet de traitement documentaire intelligent.

Le dataset couvre 3 types de documents :
- facture
- attestation URSSAF
- RIB

Il est conçu pour tester :
- la classification documentaire
- l'extraction de champs
- la validation métier
- la robustesse sur documents dégradés

---

## Structure

```text
dataset/
├── raw/
│   ├── facture/
│   ├── urssaf/
│   ├── rib/
│   └── degraded/
├── ground_truth/
│   ├── suppliers.json
│   └── expected_cases.json
├── templates/
├── generate_base_dataset.py
└── README.md