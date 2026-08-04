import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_email_verified', True)
        extra_fields.setdefault('user_type', User.UserType.SUPER_ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class UserType(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Administrator'
        SYSTEM_ADMIN = 'SYSTEM_ADMIN', 'System Administrator'
        CLINIC_ADMIN = 'CLINIC_ADMIN', 'Clinic Administrator'
        VETERINARIAN = 'VETERINARIAN', 'Veterinarian'
        VET_TECHNICIAN = 'VET_TECHNICIAN', 'Veterinary Technician'
        FARMER = 'FARMER', 'Farmer'
        LAB_STAFF = 'LAB_STAFF', 'Laboratory Staff'
        PHARMACIST = 'PHARMACIST', 'Pharmacist'
        RECEPTIONIST = 'RECEPTIONIST', 'Receptionist'
        GOVERNMENT_OFFICER = 'GOVERNMENT_OFFICER', 'Government Officer / Epidemiologist'

    username = None  # Use email as unique identifier
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=30, blank=True, default='')
    user_type = models.CharField(
        max_length=30,
        choices=UserType.choices,
        default=UserType.FARMER,
        db_index=True
    )
    lga = models.CharField(max_length=100, blank=True, default='Kano Municipal')
    address = models.TextField(blank=True, default='')
    avatar = models.URLField(blank=True, default='')
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=64, blank=True, default='')
    password_reset_token = models.CharField(max_length=64, blank=True, default='')
    password_reset_expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    def issue_email_verification_token(self):
        token = uuid.uuid4().hex
        self.email_verification_token = token
        self.save(update_fields=['email_verification_token'])
        return token

    def issue_password_reset_token(self):
        token = uuid.uuid4().hex
        self.password_reset_token = token
        self.password_reset_expires_at = timezone.now() + timedelta(hours=1)
        self.save(update_fields=['password_reset_token', 'password_reset_expires_at'])
        return token

    def __str__(self):
        return f"{self.full_name} ({self.email}) - {self.get_user_type_display()}"
