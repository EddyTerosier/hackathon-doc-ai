from mongoengine import connect
from mongoengine.connection import disconnect, get_connection

from django.conf import settings


def initialize_mongo():
    try:
        get_connection()
        return
    except Exception:
        pass

    connection_kwargs = {
        "db": settings.MONGO_DB_NAME,
        "host": settings.MONGO_HOST,
        "port": settings.MONGO_PORT,
    }

    if settings.MONGO_MOCK:
        import mongomock

        connection_kwargs["mongo_client_class"] = mongomock.MongoClient

    if settings.MONGO_USERNAME:
        connection_kwargs["username"] = settings.MONGO_USERNAME
    if settings.MONGO_PASSWORD:
        connection_kwargs["password"] = settings.MONGO_PASSWORD
        connection_kwargs["authentication_source"] = settings.MONGO_AUTH_SOURCE

    connect(**connection_kwargs)


def reconnect_mongo_for_tests():
    try:
        disconnect()
    except Exception:
        pass
    initialize_mongo()
