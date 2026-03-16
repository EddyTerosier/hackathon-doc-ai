from django.contrib.auth.hashers import check_password, make_password
from mongoengine import DateTimeField, Document, EmailField, StringField
import datetime


class User(Document):
    ROLE_EMPLOYEE = "Employee"
    ROLE_ACCOUNTANT = "Accountant"
    ROLE_CHOICES = (ROLE_EMPLOYEE, ROLE_ACCOUNTANT)

    nom = StringField(required=True, max_length=120)
    prenom = StringField(required=True, max_length=120)
    role = StringField(required=True, choices=ROLE_CHOICES)
    email = EmailField(required=True, unique=True)
    password = StringField(required=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "users",
        "indexes": ["email"],
    }

    @property
    def is_authenticated(self):
        return True

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def save(self, *args, **kwargs):
        self.updated_at = datetime.datetime.utcnow()
        return super().save(*args, **kwargs)
