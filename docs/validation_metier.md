# Validation métier

## Objectif

La validation métier a pour rôle de contrôler la cohérence des informations extraites à partir des documents fournisseurs.

Elle intervient après :

* la classification documentaire
* l’OCR ou l’extraction de texte
* l’extraction des champs clés

Son but est de transformer des données brutes extraites en un **résultat métier exploitable**, avec :

* un **statut global**
* une **liste d’anomalies**
* une **aide à la décision** pour l’opérateur

---

## Rôle dans le pipeline

La validation métier se situe après l’extraction des données.

### Ordre de traitement

1. upload document
2. lecture / OCR
3. classification
4. extraction des champs
5. **validation métier**
6. restitution dans l’interface
7. sauvegarde en base

---

## Périmètre de validation

Dans le cadre du projet, la validation métier porte sur les documents suivants :

* facture
* attestation URSSAF
* RIB

Les contrôles se font :

* au niveau d’un document unique
* au niveau d’un dossier fournisseur regroupant plusieurs documents

---

## Objectifs fonctionnels

La validation métier doit permettre de :

* vérifier la présence des champs essentiels
* détecter les incohérences entre documents
* identifier les documents expirés
* signaler les données manquantes ou suspectes
* produire un statut lisible pour le métier

---

## Règles de cohérence

### 1. Cohérence du SIRET

Le SIRET extrait de la facture doit être identique au SIRET extrait de l’attestation URSSAF.

#### Exemple d’anomalie

* SIRET facture : `23456789012345`
* SIRET attestation : `99999999999999`

#### Résultat attendu

* anomalie détectée
* dossier potentiellement **non conforme**

---

### 2. Validité de l’attestation URSSAF

La date d’expiration de l’attestation URSSAF doit être supérieure ou égale à la date du jour.

#### Exemple d’anomalie

* date expiration : `2026-01-15`
* document traité après cette date

#### Résultat attendu

* anomalie détectée
* dossier **non conforme**

---

### 3. Cohérence des montants facture

Le montant TTC doit être supérieur ou égal au montant HT.

#### Exemple d’anomalie

* montant HT : `1500.00`
* montant TTC : `1400.00`

#### Résultat attendu

* anomalie détectée
* facture **non conforme**

---

### 4. Présence de l’IBAN

Le RIB doit contenir un IBAN.

#### Résultat attendu

* si absent : anomalie
* dossier à vérifier ou non conforme selon la politique retenue

---

### 5. Présence du BIC

Le RIB doit idéalement contenir un BIC.

#### Résultat attendu

* si absent : anomalie
* dossier généralement **à vérifier**

---

### 6. Présence des champs essentiels

Chaque type de document doit contenir les champs indispensables.

#### Facture

* fournisseur
* SIRET
* date d’émission
* montant HT
* montant TTC

#### Attestation URSSAF

* entreprise
* SIRET
* date d’expiration

#### RIB

* titulaire
* IBAN
* BIC

Si un champ critique est absent ou inexploitable :

* anomalie détectée
* statut au minimum **à vérifier**

---

## Statut global

À la fin de la validation, le système attribue un statut global au dossier fournisseur.

### Statuts utilisés

* `conforme`
* `a_verifier`
* `non_conforme`

---

### `conforme`

Aucune anomalie bloquante détectée.

#### Exemples

* SIRET cohérent
* attestation valide
* montants cohérents
* IBAN et BIC présents

---

### `a_verifier`

Le dossier contient une anomalie partielle, un doute, ou une donnée manquante non bloquante.

#### Exemples

* BIC absent
* document difficile à lire
* OCR incertain
* champ non critique manquant

---

### `non_conforme`

Le dossier présente une incohérence métier bloquante.

#### Exemples

* SIRET incohérent entre facture et attestation
* attestation expirée
* montant TTC inférieur au montant HT

---

## Détection d’anomalies

La validation métier doit produire une liste explicite d’anomalies.

### Exemples d’anomalies possibles

* `SIRET incohérent entre facture et attestation`
* `Attestation URSSAF expirée`
* `Montant TTC inférieur au montant HT`
* `IBAN manquant sur le RIB`
* `BIC manquant sur le RIB`
* `Champ critique manquant`
* `Qualité OCR potentiellement dégradée`

L’objectif est de fournir un message compréhensible directement par un utilisateur métier.

---

## Niveau de validation

### Validation unitaire

Contrôle d’un document seul.

#### Exemples

* vérifier que le RIB contient un IBAN
* vérifier que la facture contient un montant HT et TTC
* vérifier qu’une date d’expiration est présente

### Validation croisée

Contrôle entre plusieurs documents du même fournisseur.

#### Exemples

* comparer le SIRET entre facture et attestation
* consolider les informations fournisseur
* produire un statut global de conformité

---

## Entrées attendues

La validation métier consomme des données structurées issues de l’étape d’extraction.

### Exemple d’entrée

```json
{
  "supplier_id": "SUP001",
  "documents": [
    {
      "document_type": "facture",
      "fields": {
        "supplier_name": "Alpha Conseil",
        "siret": "12345678901234",
        "date_emission": "2026-03-10",
        "montant_ht": 1200.5,
        "montant_ttc": 1440.6
      }
    },
    {
      "document_type": "attestation_urssaf",
      "fields": {
        "supplier_name": "Alpha Conseil",
        "siret": "12345678901234",
        "date_expiration": "2026-06-30"
      }
    },
    {
      "document_type": "rib",
      "fields": {
        "supplier_name": "Alpha Conseil",
        "iban": "FR7612345678901234567890123",
        "bic": "AGRIFRPP"
      }
    }
  ]
}
```

---

## Sortie attendue

La validation métier doit produire un résultat structuré.

### Exemple de sortie

```json
{
  "supplier_id": "SUP001",
  "status": "conforme",
  "issues": []
}
```

### Exemple avec anomalies

```json
{
  "supplier_id": "SUP002",
  "status": "non_conforme",
  "issues": [
    "SIRET incohérent entre facture et attestation"
  ]
}
```

---

## Cas couverts dans le dataset

Le dataset du projet couvre plusieurs cas de validation métier :

* dossier conforme
* SIRET incohérent
* attestation expirée
* document dégradé
* BIC manquant
* TTC inférieur au HT

Ces scénarios permettent de tester à la fois :

* les règles unitaires
* les règles croisées
* le calcul du statut global

---

## Résultat attendu côté interface

Dans l’application, la validation métier doit être visible de façon simple.

### Affichage attendu

* statut global du dossier
* liste des anomalies
* champs extraits consolidés
* aide à la décision pour l’opérateur

---

## Principes de conception

La validation métier doit rester :

* simple
* explicable
* lisible
* maintenable

Le projet ne cherche pas à produire un moteur de règles complexe, mais une logique claire et démontrable dans un cadre de hackathon.

---

## Résumé

La validation métier transforme les données extraites en décision opérationnelle.

Elle permet :

* de contrôler la cohérence des documents
* d’identifier les anomalies importantes
* d’attribuer un statut global au dossier
* d’aider l’utilisateur à valider ou rejeter un fournisseur