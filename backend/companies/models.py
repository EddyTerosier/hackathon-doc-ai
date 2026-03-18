import datetime

from mongoengine import DateTimeField, Document, EmailField, StringField


class TimeStampedDocument(Document):
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    meta = {"abstract": True}

    def save(self, *args, **kwargs):
        self.updated_at = datetime.datetime.utcnow()
        return super().save(*args, **kwargs)


class Company(TimeStampedDocument):
    name = StringField(required=True, max_length=255)
    registration_number = StringField(max_length=100)
    siret = StringField(max_length=14)
    vat_number = StringField(max_length=32)
    email = EmailField()

    meta = {
        "collection": "companies",
        "indexes": ["name", "registration_number", "siret", "vat_number"],
    }
