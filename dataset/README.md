# Dataset - Hackathon Doc AI

## Objectif

Ce dossier contient le jeu de données de test du projet de traitement documentaire intelligent.

Le dataset a été conçu pour simuler un traitement de documents administratifs fournisseurs dans un contexte simple, local et reproductible.

Il permet de tester :

* la classification automatique des documents
* l'extraction des champs clés
* la validation métier
* la robustesse sur des documents dégradés
* le traitement de fichiers PDF et d'images

---

## Types de documents couverts

Le dataset contient 3 types de documents :

* **Facture**
* **Attestation URSSAF**
* **RIB**

---

## Scénarios couverts

Le dataset repose sur 6 fournisseurs fictifs, chacun associé à un scénario métier.

### SUP001 — conforme

Cas nominal sans anomalie.

### SUP002 — siret_incoherent

Le SIRET de la facture est différent du SIRET de l’attestation URSSAF.

### SUP003 — attestation_expired

L’attestation URSSAF est expirée.

### SUP004 — invoice_degraded

La facture existe aussi en variantes dégradées pour simuler une lecture OCR plus difficile.

### SUP005 — rib_missing_bic

Le RIB ne contient pas de BIC.

### SUP006 — ttc_lower_than_ht

Le montant TTC est inférieur au montant HT sur la facture.

---

## Structure du dossier

```text
dataset/
├── raw/
│   ├── facture/
│   ├── urssaf/
│   ├── rib/
│   └── degraded/
├── raw_images/
│   ├── facture/
│   ├── urssaf/
│   ├── rib/
│   └── degraded/
├── ground_truth/
│   ├── suppliers.json
│   ├── expected_documents.json
│   └── expected_cases.json
├── templates/
├── clean_generated_images.py
├── clean_generated_pdfs.py
├── generate_base_dataset.py
├── generate_base_images.py
└── README.md
```

---

## Contenu des sous-dossiers

### `raw/`

Contient les documents PDF générés.

#### `raw/facture/`

Contient les factures PDF.

#### `raw/urssaf/`

Contient les attestations URSSAF PDF.

#### `raw/rib/`

Contient les RIB PDF.

#### `raw/degraded/`

Contient les variantes dégradées PDF, avec vrai flou et vraie rotation pour certains cas.

---

### `raw_images/`

Contient les documents image générés au format PNG.

#### `raw_images/facture/`

Contient les factures PNG.

#### `raw_images/urssaf/`

Contient les attestations URSSAF PNG.

#### `raw_images/rib/`

Contient les RIB PNG.

#### `raw_images/degraded/`

Contient les variantes dégradées PNG, avec vrai flou et vraie rotation pour certains cas.

---

## Ground truth

### `ground_truth/suppliers.json`

Ce fichier contient les données de référence pour chaque fournisseur fictif.

On y retrouve notamment :

* `supplier_id`
* `scenario`
* `supplier_name`
* `siret`
* `tva`
* `iban`
* `bic`
* `date_emission`
* `date_expiration`
* `montant_ht`
* `montant_ttc`
* `invoice_siret`
* `urssaf_siret`
* `rib_iban`
* `rib_bic`
* `degraded_documents`

Ce fichier sert de base de génération des documents.

### `ground_truth/expected_cases.json`

Ce fichier contient le résultat métier attendu au niveau du dossier fournisseur.

Pour chaque fournisseur, on y trouve :

* le scénario
* le statut global attendu
* la liste des anomalies attendues

Ce fichier sert à vérifier si la logique de validation inter-documents fonctionne correctement.

---

## Convention de nommage

### Factures PDF

Format :
`FAC_<SUPPLIER_ID>_<SCENARIO>.pdf`

Exemple :
`FAC_SUP001_conforme.pdf`

### Attestations URSSAF PDF

Format :
`URS_<SUPPLIER_ID>_<SCENARIO>.pdf`

Exemple :
`URS_SUP002_siret_incoherent.pdf`

### RIB PDF

Format :
`RIB_<SUPPLIER_ID>_<SCENARIO>.pdf`

Exemple :
`RIB_SUP005_rib_missing_bic.pdf`

### Variantes PDF dégradées

Format :
`FAC_<SUPPLIER_ID>_<SCENARIO>_<VARIANTE>.pdf`

Exemples :

* `FAC_SUP004_invoice_degraded_blur.pdf`
* `FAC_SUP004_invoice_degraded_rotate.pdf`

### Images PNG

Même logique de nommage avec l’extension `.png`.

Exemples :

* `FAC_SUP001_conforme.png`
* `URS_SUP002_siret_incoherent.png`
* `RIB_SUP005_rib_missing_bic.png`
* `FAC_SUP004_invoice_degraded_blur.png`

---

## Champs présents par type de document

### Facture

Champs attendus :

* `supplier_name`
* `siret`
* `tva`
* `date_emission`
* `montant_ht`
* `montant_ttc`

### Attestation URSSAF

Champs attendus :

* `supplier_name`
* `siret`
* `date_expiration`

### RIB

Champs attendus :

* `supplier_name`
* `iban`
* `bic`

---

## Statuts métier attendus

Les statuts globaux utilisés dans le dataset sont :

* `conforme`
* `a_verifier`
* `non_conforme`

### Signification

* **conforme** : aucune anomalie détectée
* **a_verifier** : anomalie partielle ou document incertain
* **non_conforme** : incohérence métier bloquante

---

## Prérequis

Créer et activer l’environnement virtuel :

```bash
python -m venv .venv
source .venv\Scripts\Activate
python -m pip install --upgrade pip
```

Installer les dépendances nécessaires :

```bash
pip install reportlab pillow
```

---

## Génération des PDF

Le dataset PDF est généré automatiquement avec :

```bash
python dataset/generate_base_dataset.py
```

---

## Nettoyage des PDF générés

Pour supprimer les PDF générés dans les dossiers `raw/`, utilisez :

```bash
python dataset/clean_generated_pdfs.py
```

Ce script supprime les fichiers PDF présents dans :

* `dataset/raw/facture/`
* `dataset/raw/urssaf/`
* `dataset/raw/rib/`
* `dataset/raw/degraded/`

---

## Génération des images PNG

Le dataset image est généré automatiquement avec :

```bash
python dataset/generate_base_images.py
```

---

## Nettoyage des images générées

Pour supprimer les images générées dans les dossiers `raw_images/`, utilisez :

```bash
python dataset/clean_generated_images.py
```

Ce script supprime les fichiers image présents dans :

* `dataset/raw_images/facture/`
* `dataset/raw_images/urssaf/`
* `dataset/raw_images/rib/`
* `dataset/raw_images/degraded/`

---

## Makefile

Un `Makefile` est disponible à la racine du projet pour simplifier les commandes.

### Générer les PDF

```bash
make dataset-generate
```

### Nettoyer les PDF

```bash
make dataset-clean
```

### Nettoyer puis regénérer les PDF

```bash
make dataset-reset
```

### Générer les images PNG

```bash
make dataset-images-generate
```

### Nettoyer les images PNG

```bash
make dataset-images-clean
```

### Nettoyer puis regénérer les images PNG

```bash
make dataset-images-reset
```

---

## Résultat attendu après génération

### PDF

Le script PDF génère :

* 6 factures PDF
* 6 attestations URSSAF PDF
* 6 RIB PDF
* 2 variantes dégradées de facture PDF

Soit un total de **20 documents PDF**.

### Images PNG

Le script image génère :

* 6 factures PNG
* 6 attestations URSSAF PNG
* 6 RIB PNG
* 2 variantes dégradées de facture PNG

Soit un total de **20 images PNG**.

---

## Rôle du dataset dans le projet

Ce dataset sert de base de test pour l’ensemble du pipeline :

1. upload des documents
2. lecture du contenu
3. OCR ou extraction de texte
4. classification du type documentaire
5. extraction des champs
6. validation métier
7. restitution dans l’interface

---

## Limites du dataset

Ce dataset est volontairement simple :

* données fictives
* volumétrie réduite
* mise en page contrôlée
* nombre limité de scénarios

Il s’agit d’un dataset de démonstration pour hackathon, pas d’un corpus de production.

---

## Évolutions possibles

Le dataset pourra être enrichi avec :

* davantage de scénarios métier
* plus de documents par fournisseur
* d’autres formats image
* compression JPEG
* documents encore plus dégradés
* scans plus réalistes

---

## Remarques

* Tous les documents sont fictifs.
* Les identifiants et coordonnées bancaires sont uniquement utilisés à des fins de test.
* Les variantes `blur` et `rotate` appliquent une vraie transformation sur les images, et sur les PDF dégradés via génération image puis export PDF.
* Le dataset est pensé pour rester simple, cohérent et facilement régénérable.