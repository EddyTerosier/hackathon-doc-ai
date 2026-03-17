from rest_framework import serializers

from .models import Company


class CompanySerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=255)
    registration_number = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    siret = serializers.CharField(max_length=14, required=False, allow_blank=True)
    vat_number = serializers.CharField(max_length=32, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "name": instance.name,
            "registration_number": instance.registration_number or "",
            "siret": instance.siret or "",
            "vat_number": instance.vat_number or "",
            "email": instance.email or "",
            "created_at": instance.created_at.isoformat(),
            "updated_at": instance.updated_at.isoformat(),
        }

    def create(self, validated_data):
        company = Company(**validated_data)
        company.save()
        return company

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance
