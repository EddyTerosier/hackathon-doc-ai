# Backend Django REST + MongoDB

## Apps

- `users` pour l'authentification et les utilisateurs
- `companies` pour les entreprises
- `suppliers` pour les fournisseurs
- `documents` pour les groupes de documents et les fichiers

## Endpoints

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `GET /api/auth/me/`
- `POST /api/auth/refresh/`
- `GET/POST /api/companies/`
- `GET/PATCH/DELETE /api/companies/<company_id>/`
- `GET/POST /api/suppliers/`
- `GET/PATCH/DELETE /api/suppliers/<supplier_id>/`
- `GET/POST /api/document-groups/`
- `GET/PATCH/DELETE /api/document-groups/<group_id>/`
- `GET/POST /api/document-groups/<group_id>/documents/`
- `DELETE /api/documents/<document_id>/`

## Exemple d'inscription

```json
{
  "last_name": "Dupont",
  "first_name": "Marie",
  "role": "Employee",
  "email": "marie.dupont@example.com",
  "password": "motdepasse123"
}
```

## Lancer avec Docker

```bash
docker compose up --build
```

Les commandes Django lancees en local lisent automatiquement les variables depuis `backend/.env` et, a defaut, `backend/.env.example`.

## Voir la base MongoDB

Une interface `mongo-express` est disponible apres le lancement Docker :

```text
http://localhost:8081
```

Identifiants de connexion a l'interface :
- utilisateur : `admin`
- mot de passe : `admin123`

## Lancer les tests

```bash
python manage.py test
```

## Inserer des donnees de base

La commande ci-dessous ajoute 4 utilisateurs par defaut :
- 2 comptes admin avec le role `Accountant`
- 2 comptes avec le role `Employee`

```bash
python manage.py seed_users
```

Comptes crees :
- `admin1@hackathon.local` / `Admin12345!`
- `admin2@hackathon.local` / `Admin12345!`
- `salarie1@hackathon.local` / `Salarie12345!`
- `salarie2@hackathon.local` / `Salarie12345!`

## Inserer des donnees metier

La commande ci-dessous ajoute des entreprises, fournisseurs, groupes documentaires
et documents de demonstration inspires du use case :

```bash
python manage.py seed_business_data
```

Elle cree notamment :
- 2 entreprises
- 2 fournisseurs
- 2 groupes documentaires
- 5 documents de demonstration

Pour avoir aussi un proprietaire sur les groupes, lance d'abord :

```bash
python manage.py seed_users
```

## Header d'authentification

```text
Authorization: Bearer <access_token>
```

## Document groups

Un document group peut :
- etre lie a une entreprise
- etre lie a un fournisseur
- etre lie aux deux
- ne pas etre lie du tout

Etats disponibles :
- `pending`
- `complete`
- `processing`
- `non_compliant`
- `compliant`

Formats de documents acceptes :
- `pdf`
- `png`
- `jpg`
- `jpeg`

Champs metier ajoutes a partir du use case :
- `Company` : `siret`, `vat_number`
- `Supplier` : `siret`, `vat_number`, `iban`, `bic`, `urssaf_expiration_date`
- `DocumentGroup` : `extracted_summary`, `anomalies`, `compliance_notes`, `non_compliance_reason`, dates de traitement
- `DocumentFile` : `document_type`, `analysis_status`, `ocr_text`, `extracted_data`, `anomalies`, `confidence_score`, `needs_manual_review`

Si `state = non_compliant`, il faut renseigner `non_compliance_reason`.
