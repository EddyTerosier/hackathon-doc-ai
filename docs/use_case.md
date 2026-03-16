# Use case représentatif — Contrôle documentaire d’un fournisseur

## Contexte

Une entreprise reçoit plusieurs documents administratifs d’un fournisseur avant validation dans son référentiel interne.

Les documents transmis sont :

- une facture
- une attestation URSSAF
- un RIB

Ces documents doivent être contrôlés avant intégration dans l’outil métier.

---

## Objectif

Automatiser l’analyse documentaire afin de :

- identifier le type de chaque document
- extraire les informations clés
- détecter les incohérences
- pré-remplir une fiche fournisseur / conformité
- réduire le temps de traitement manuel

---

## Acteurs

### Utilisateur principal
- opérateur administratif
- gestionnaire conformité
- assistant comptable

### Système
- plateforme de traitement documentaire
- moteur OCR
- moteur d’extraction
- moteur de validation métier

---

## Préconditions

- l’utilisateur dispose d’un lot de documents à analyser
- les documents sont au format PDF ou image
- le système est lancé localement via Docker

---

## Déclencheur

L’utilisateur dépose un ou plusieurs documents dans l’interface d’upload.

---

## Scénario nominal

### Étape 1 — Upload
L’utilisateur charge les documents suivants :
- `FAC_SUP001_conforme.pdf`
- `URS_SUP001_conforme.pdf`
- `RIB_SUP001_conforme.pdf`

### Étape 2 — Stockage brut
Le système enregistre les fichiers dans l’espace de stockage brut.

### Étape 3 — Lecture / OCR
Le système lit les documents et extrait leur contenu texte.

### Étape 4 — Classification
Le système identifie automatiquement :
- document 1 = facture
- document 2 = attestation URSSAF
- document 3 = RIB

### Étape 5 — Extraction des champs
Le système extrait :

#### Facture
- fournisseur : Alpha Conseil
- SIRET : 12345678901234
- TVA : FR12123456789
- date d’émission : 2026-03-10
- montant HT : 1200.50
- montant TTC : 1440.60

#### Attestation URSSAF
- entreprise : Alpha Conseil
- SIRET : 12345678901234
- date d’expiration : 2026-06-30

#### RIB
- titulaire : Alpha Conseil
- IBAN : FR7612345678901234567890123
- BIC : AGRIFRPP

### Étape 6 — Validation métier
Le système compare les informations entre documents :
- SIRET facture = SIRET attestation
- attestation non expirée
- IBAN présent
- BIC présent
- TTC supérieur au HT

### Étape 7 — Résultat global
Le système attribue le statut :
- **conforme**

### Étape 8 — Restitution métier
Le système pré-remplit automatiquement la fiche fournisseur / conformité dans l’interface.

---

## Résultat attendu

La fiche affichée contient :

- nom fournisseur : Alpha Conseil
- SIRET : 12345678901234
- TVA : FR12123456789
- IBAN : FR7612345678901234567890123
- BIC : AGRIFRPP
- date facture : 2026-03-10
- montant HT : 1200.50
- montant TTC : 1440.60
- expiration URSSAF : 2026-06-30
- statut global : conforme

---

## Scénario alternatif 1 — SIRET incohérent

### Documents chargés
- `FAC_SUP002_siret_incoherent.pdf`
- `URS_SUP002_siret_incoherent.pdf`
- `RIB_SUP002_siret_incoherent.pdf`

### Contrôle effectué
- SIRET facture = 23456789012345
- SIRET attestation = 99999999999999

### Résultat
Le système détecte une incohérence inter-documents et attribue le statut :
- **non_conforme**

### Anomalie affichée
- SIRET incohérent entre facture et attestation

---

## Scénario alternatif 2 — Attestation expirée

### Documents chargés
- `FAC_SUP003_attestation_expired.pdf`
- `URS_SUP003_attestation_expired.pdf`
- `RIB_SUP003_attestation_expired.pdf`

### Contrôle effectué
- date expiration attestation = 2026-01-15
- date actuelle postérieure à la date d’expiration

### Résultat
Le système attribue le statut :
- **non_conforme**

### Anomalie affichée
- Attestation URSSAF expirée

---

## Scénario alternatif 3 — Document dégradé

### Documents chargés
- `FAC_SUP004_invoice_degraded_blur.pdf`
- `URS_SUP004_invoice_degraded.pdf`
- `RIB_SUP004_invoice_degraded.pdf`

### Contrôle effectué
Le système tente de lire une facture dégradée avec flou.

### Résultat possible
- certains champs sont extraits correctement
- certains champs peuvent être incertains
- le système attribue le statut :
  - **a_verifier**

### Anomalie affichée
- qualité OCR potentiellement dégradée sur la facture

---

## Postconditions

Après traitement :

- les documents restent stockés
- les champs extraits sont structurés
- le statut métier est calculé
- les anomalies sont affichées
- la fiche fournisseur est pré-remplie

---

## Valeur métier

Ce use case illustre le gain principal du projet :

- diminution de la saisie manuelle
- réduction des erreurs humaines
- accélération du contrôle documentaire
- meilleure traçabilité
- détection plus rapide des incohérences administratives

---

## Résumé

Ce use case montre comment la plateforme transforme un lot de documents administratifs bruts en une information métier exploitable, contrôlée et directement utilisable par un opérateur.