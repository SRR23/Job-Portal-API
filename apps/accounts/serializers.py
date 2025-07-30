from rest_framework import serializers
from .models import User

class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'confirm_password', 'role', 'first_name', 
                 'last_name', 'organization_name', 'website']
        
    def validate(self, data):
        # Validate password confirmation
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match"}
            )
        
        role = data.get('role')
        
        # Validate fields based on role
        if role == User.Role.JOB_SEEKER:
            if not data.get('first_name') or not data.get('last_name'):
                raise serializers.ValidationError(
                    "First name and last name are required for job seekers"
                )
            if data.get('organization_name') or data.get('website'):
                raise serializers.ValidationError(
                    "Organization fields should not be provided for job seekers"
                )
        elif role == User.Role.ORGANIZATION:
            if not data.get('organization_name'):
                raise serializers.ValidationError(
                    "Organization name is required for organizations"
                )
            if data.get('first_name') or data.get('last_name'):
                raise serializers.ValidationError(
                    "Personal name fields should not be provided for organizations"
                )
        
        return data
    
    def create(self, validated_data):
        # Remove confirm_password from validated_data before creating user
        validated_data.pop('confirm_password')
        return User.objects.create_user(**validated_data)

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'role', 'first_name', 'last_name', 
                 'organization_name', 'website', 'is_active', 'date_joined']
        read_only_fields = ['email', 'role', 'is_active', 'date_joined']
    
    def validate(self, data):
        role = self.instance.role if self.instance else data.get('role')
        
        # Validate fields based on role
        if role == User.Role.JOB_SEEKER:
            if data.get('organization_name') or data.get('website'):
                raise serializers.ValidationError(
                    "Organization fields cannot be set for job seekers"
                )
        elif role == User.Role.ORGANIZATION:
            if data.get('first_name') or data.get('last_name'):
                raise serializers.ValidationError(
                    "Personal name fields cannot be set for organizations"
                )
        
        return data