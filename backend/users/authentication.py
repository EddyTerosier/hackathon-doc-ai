from bson import ObjectId
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed

from .models import User
from .tokens import decode_token


class MongoJWTAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request).decode("utf-8")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            raise AuthenticationFailed("En-tete Authorization invalide.")

        payload = decode_token(parts[1], expected_type="access")
        user = User.objects(id=ObjectId(payload["sub"])).first()
        if not user:
            raise AuthenticationFailed("Utilisateur introuvable.")
        return (user, None)
