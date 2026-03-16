from django.test import TestCase
from django.core.management import call_command
from rest_framework.test import APIClient

from .models import User
from .mongo import reconnect_mongo_for_tests


class AuthAPITests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        reconnect_mongo_for_tests()

    def setUp(self):
        reconnect_mongo_for_tests()
        User.drop_collection()
        self.client = APIClient()
        self.register_url = "/api/auth/register/"
        self.login_url = "/api/auth/login/"
        self.me_url = "/api/auth/me/"
        self.refresh_url = "/api/auth/refresh/"
        self.user_payload = {
            "nom": "Dupont",
            "prenom": "Marie",
            "role": "Salarie",
            "email": "marie.dupont@example.com",
            "password": "motdepasse123",
        }

    def test_register_creates_user_and_returns_tokens(self):
        response = self.client.post(self.register_url, self.user_payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertIn("tokens", response.data)
        self.assertEqual(response.data["user"]["email"], self.user_payload["email"])
        self.assertEqual(User.objects.count(), 1)

    def test_login_returns_tokens_for_valid_credentials(self):
        user = User(
            nom="Dupont",
            prenom="Marie",
            role="Salarie",
            email="marie.dupont@example.com",
        )
        user.set_password("motdepasse123")
        user.save()

        response = self.client.post(
            self.login_url,
            {"email": "marie.dupont@example.com", "password": "motdepasse123"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])

    def test_me_requires_bearer_token(self):
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, 403)

    def test_me_returns_current_user(self):
        register_response = self.client.post(
            self.register_url, self.user_payload, format="json"
        )
        access_token = register_response.data["tokens"]["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["nom"], "Dupont")
        self.assertEqual(response.data["role"], "Salarie")

    def test_refresh_returns_new_tokens(self):
        register_response = self.client.post(
            self.register_url, self.user_payload, format="json"
        )
        refresh_token = register_response.data["tokens"]["refresh"]

        response = self.client.post(
            self.refresh_url, {"refresh": refresh_token}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_register_rejects_duplicate_email(self):
        self.client.post(self.register_url, self.user_payload, format="json")
        response = self.client.post(self.register_url, self.user_payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)


class SeedUsersCommandTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        reconnect_mongo_for_tests()

    def setUp(self):
        reconnect_mongo_for_tests()
        User.drop_collection()

    def test_seed_users_command_creates_four_default_users(self):
        call_command("seed_users")

        self.assertEqual(User.objects.count(), 4)
        self.assertEqual(User.objects(role=User.ROLE_COMPTABLE).count(), 2)
        self.assertEqual(User.objects(role=User.ROLE_SALARIE).count(), 2)
        self.assertIsNotNone(User.objects(email="admin1@hackathon.local").first())

    def test_seed_users_command_is_idempotent(self):
        call_command("seed_users")
        call_command("seed_users")

        self.assertEqual(User.objects.count(), 4)
