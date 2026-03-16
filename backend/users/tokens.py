from datetime import datetime, timezone

import jwt
from bson import ObjectId
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed


def _build_payload(user_id, token_type, lifetime):
    now = datetime.now(timezone.utc)
    return {
        "sub": str(user_id),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
    }


def generate_tokens_for_user(user):
    access_payload = _build_payload(
        user.id, "access", settings.JWT_ACCESS_LIFETIME
    )
    refresh_payload = _build_payload(
        user.id, "refresh", settings.JWT_REFRESH_LIFETIME
    )
    return {
        "access": jwt.encode(
            access_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        ),
        "refresh": jwt.encode(
            refresh_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        ),
    }


def decode_token(token, expected_type="access"):
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationFailed("Le token a expire.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationFailed("Token invalide.") from exc

    if payload.get("type") != expected_type:
        raise AuthenticationFailed("Type de token invalide.")

    user_id = payload.get("sub")
    if not user_id or not ObjectId.is_valid(user_id):
        raise AuthenticationFailed("Utilisateur invalide.")

    return payload
