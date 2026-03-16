# Backend Django REST + MongoDB

## Endpoints

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `GET /api/auth/me/`
- `POST /api/auth/refresh/`

## Exemple d'inscription

```json
{
  "nom": "Dupont",
  "prenom": "Marie",
  "role": "Salarie",
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
- 2 comptes admin avec le role `Comptable`
- 2 comptes avec le role `Salarie`

```bash
python manage.py seed_users
```

Comptes crees :
- `admin1@hackathon.local` / `Admin12345!`
- `admin2@hackathon.local` / `Admin12345!`
- `salarie1@hackathon.local` / `Salarie12345!`
- `salarie2@hackathon.local` / `Salarie12345!`

## Header d'authentification

```text
Authorization: Bearer <access_token>
```
