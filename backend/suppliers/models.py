import datetime

from mongoengine import DateField, DateTimeField, Document, EmailField, StringField


class TimeStampedDocument(Document):
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    meta = {"abstract": True}

    def save(self, *args, **kwargs):
        self.updated_at = datetime.datetime.utcnow()
        return super().save(*args, **kwargs)


class Supplier(TimeStampedDocument):
    name = StringField(required=True, max_length=255)
    registration_number = StringField(max_length=100)
    siret = StringField(max_length=14)
    vat_number = StringField(max_length=32)
    iban = StringField(max_length=34)
    bic = StringField(max_length=11)
    urssaf_expiration_date = DateField()
    email = EmailField()

    meta = {
        "collection": "suppliers",
        "indexes": ["name", "registration_number", "siret", "vat_number"],
    }
