from django.core.management.base import BaseCommand

from users.models import User


SEED_USERS = [
    {
        "nom": "Martin",
        "prenom": "Alice",
        "role": User.ROLE_ACCOUNTANT,
        "email": "admin1@hackathon.local",
        "password": "Admin12345!",
    },
    {
        "nom": "Bernard",
        "prenom": "Thomas",
        "role": User.ROLE_ACCOUNTANT,
        "email": "admin2@hackathon.local",
        "password": "Admin12345!",
    },
    {
        "nom": "Dubois",
        "prenom": "Sophie",
        "role": User.ROLE_EMPLOYEE,
        "email": "salarie1@hackathon.local",
        "password": "Salarie12345!",
    },
    {
        "nom": "Petit",
        "prenom": "Lucas",
        "role": User.ROLE_EMPLOYEE,
        "email": "salarie2@hackathon.local",
        "password": "Salarie12345!",
    },
]


class Command(BaseCommand):
    help = (
        "Insere 2 comptes admin (role Accountant) et 2 comptes Employee "
        "dans MongoDB sans creer de doublons."
    )

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for seed_data in SEED_USERS:
            user = User.objects(email=seed_data["email"]).first()

            if user is None:
                user = User(
                    nom=seed_data["nom"],
                    prenom=seed_data["prenom"],
                    role=seed_data["role"],
                    email=seed_data["email"],
                )
                user.set_password(seed_data["password"])
                user.save()
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Utilisateur cree : {seed_data['email']} ({seed_data['role']})"
                    )
                )
                continue

            user.nom = seed_data["nom"]
            user.prenom = seed_data["prenom"]
            user.role = seed_data["role"]
            user.set_password(seed_data["password"])
            user.save()
            updated_count += 1
            self.stdout.write(
                self.style.WARNING(
                    f"Utilisateur mis a jour : {seed_data['email']} ({seed_data['role']})"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed termine. Crees: {created_count}, mis a jour: {updated_count}."
            )
        )
