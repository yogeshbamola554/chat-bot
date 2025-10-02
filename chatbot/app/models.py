from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from datetime import timedelta


# -------------------------------
# User Manager
# -------------------------------
class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        """Create and save a regular user with phone number"""
        if not phone:
            raise ValueError("The Phone number is required")
        phone = str(phone).strip()
        user = self.model(phone=phone, **extra_fields)
        user.set_unusable_password()  # we’re using OTP instead of passwords
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        """Create and save a superuser"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(phone, password, **extra_fields)


# -------------------------------
# User Model
# -------------------------------
class User(AbstractBaseUser, PermissionsMixin):
    phone = models.CharField(max_length=15, unique=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # required for admin
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []  # createsuperuser won’t ask for email/username

    objects = UserManager()

    def __str__(self):
        return self.phone


# -------------------------------
# OTP Model
# -------------------------------
class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        """OTP expires in 5 minutes"""
        return timezone.now() > self.created_at + timedelta(minutes=5)

    def __str__(self):
        return f"OTP {self.code} for {self.user.phone}"


# -------------------------------
# Chat History Model
# -------------------------------
class ChatHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chats")
    sender = models.CharField(
        max_length=10,
        choices=(("user", "User"), ("bot", "Bot"))
    )
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.phone} | {self.sender}: {self.message[:30]}"
