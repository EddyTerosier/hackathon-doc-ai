from django.core.management.base import BaseCommand

from users.models import User


SEED_USERS = [
    {
        "last_name": "Martin",
        "first_name": "Alice",
        "role": User.ROLE_ACCOUNTANT,
        "email": "admin1@hackathon.local",
        "password": "Admin12345!",
    },
    {
        "last_name": "Bernard",
        "first_name": "Thomas",
        "role": User.ROLE_ACCOUNTANT,
        "email": "admin2@hackathon.local",
        "password": "Admin12345!",
    },
    {
        "last_name": "Dubois",
        "first_name": "Sophie",
        "role": User.ROLE_EMPLOYEE,
        "email": "salarie1@hackathon.local",
        "password": "Salarie12345!",
    },
    {
        "last_name": "Petit",
        "first_name": "Lucas",
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
                    last_name=seed_data["last_name"],
                    first_name=seed_data["first_name"],
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

            user.last_name = seed_data["last_name"]
            user.first_name = seed_data["first_name"]
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
