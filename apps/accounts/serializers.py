from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': str(self.user.id),
            'email': self.user.email,
            'full_name': self.user.full_name,
            'user_type': self.user.user_type,
            'lga': self.user.lga,
            'phone_number': self.user.phone_number,
        }
        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'full_name', 'phone_number', 'user_type', 'lga', 'address', 'avatar']
        read_only_fields = ['id']

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data['full_name'],
            phone_number=validated_data.get('phone_number', ''),
            user_type=validated_data.get('user_type', User.UserType.FARMER),
            lga=validated_data.get('lga', 'Kano Municipal'),
            address=validated_data.get('address', ''),
            avatar=validated_data.get('avatar', ''),
        )
        return user

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'phone_number', 'user_type', 'lga', 'address', 'avatar', 'is_email_verified', 'created_at']
        read_only_fields = ['id', 'email', 'created_at', 'is_email_verified']


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['old_password']):
            raise serializers.ValidationError({'old_password': 'Current password is incorrect.'})
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError('No user is registered with that email address.')
        return value


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def validate(self, attrs):
        user = User.objects.filter(password_reset_token=attrs['token']).first()
        if not user:
            raise serializers.ValidationError({'token': 'Invalid password reset token.'})
        if not user.password_reset_expires_at or timezone.now() > user.password_reset_expires_at:
            raise serializers.ValidationError({'token': 'Password reset token has expired.'})
        attrs['user'] = user
        return attrs


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)

    def validate(self, attrs):
        user = User.objects.filter(email_verification_token=attrs['token']).first()
        if not user:
            raise serializers.ValidationError({'token': 'Invalid email verification token.'})
        attrs['user'] = user
        return attrs


class VetLoginSerializer(serializers.Serializer):
    license_number = serializers.CharField(required=True)
    vet_code = serializers.CharField(required=True)

    def validate(self, attrs):
        license_number = attrs.get('license_number')
        vet_code = attrs.get('vet_code')

        from apps.veterinarians.models import VeterinarianProfile
        vet = VeterinarianProfile.objects.filter(license_number=license_number, vet_code=vet_code).first()
        
        if not vet:
            raise serializers.ValidationError('Invalid license number or vet code.')
        
        if not vet.user:
            raise serializers.ValidationError('No user account associated with this vet profile.')

        if not vet.user.is_active:
            raise serializers.ValidationError('This account is inactive.')

        refresh = RefreshToken.for_user(vet.user)
        
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': str(vet.user.id),
                'email': vet.user.email,
                'full_name': vet.user.full_name,
                'user_type': vet.user.user_type,
                'lga': vet.user.lga,
                'phone_number': vet.user.phone_number,
            }
        }

