# Périmètre du projet

## Documents supportés
- facture
- attestation URSSAF
- RIB

## Champs à extraire

### Facture
- supplier_name
- siret
- tva
- date_emission
- montant_ht
- montant_ttc

### Attestation URSSAF
- supplier_name
- siret
- date_expiration

### RIB
- supplier_name
- iban
- bic

## Contrôles métier
- SIRET facture == SIRET attestation
- date expiration URSSAF non dépassée
- montant TTC >= montant HT
- IBAN présent sur RIB
- BIC présent sur RIB

## Sortie métier
- statut global :
  - conforme
  - a_verifier
  - non_conforme

## Contraintes
- projet local
- dockerisé
- simple
- fonctionnel en 4 jours
- pas d'Airflow
- un seul frontend
- MongoDB