from django.db import models
from django.contrib.auth.models import AbstractUser


class Department(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=30, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Roles(models.TextChoices):
        QUALITY = "quality", "Quality"
        READER = "reader", "Reader"

    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.READER)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users"
    )
