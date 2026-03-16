from rest_framework import serializers

from .models import User


class UserSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    last_name = serializers.CharField()
    first_name = serializers.CharField()
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)
    email = serializers.EmailField()

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "last_name": instance.last_name,
            "first_name": instance.first_name,
            "role": instance.role,
            "email": instance.email,
        }


class RegisterSerializer(serializers.Serializer):
    last_name = serializers.CharField(max_length=120)
    first_name = serializers.CharField(max_length=120)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        if User.objects(email=value.lower()).first():
            raise serializers.ValidationError("Un utilisateur avec cet email existe deja.")
        return value.lower()

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        return value.lower()


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()
