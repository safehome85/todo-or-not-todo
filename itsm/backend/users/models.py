from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from .managers import CustomUserManager

class Company(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name=_("Company Name"))
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT_USER = 'client_user', _('Client User')
        CLIENT_ADMIN = 'client_admin', _('Client Admin')
        IT_SPECIALIST = 'it_specialist', _('IT Specialist')
        IT_ADMIN = 'it_admin', _('IT Admin')

    username = None
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT_USER)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email
