from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Company

User = get_user_model()

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'created_at', 'is_active']

class UserSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(), source='company', write_only=True, required=False, allow_null=True
    )
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'role', 'company', 'company_id', 'first_name', 'last_name', 'is_active']
        read_only_fields = ['role', 'company', 'is_active']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    company_name = serializers.CharField(write_only=True, required=False, help_text="If provided, creates a new company and makes this user Client Admin.")

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'company_name']

    def create(self, validated_data):
        company_name = validated_data.pop('company_name', None)

        user_role = User.Role.CLIENT_USER
        company = None

        if company_name:
            company, created = Company.objects.get_or_create(name=company_name)
            user_role = User.Role.CLIENT_ADMIN

        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=user_role,
            company=company
        )
        return user
