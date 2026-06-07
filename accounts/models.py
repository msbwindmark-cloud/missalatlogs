from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils import timezone
from datetime import timedelta

class QRToken(models.Model):
    user = models.ForeignKey(User, related_name='tokens', on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()

    def __str__(self):
        return f"Token for {self.user.username} - {self.token}"

class LoginLog(models.Model):
    LOGIN_TYPES = (
        ('NORMAL', 'Contraseña'),
        ('QR', 'Código QR'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_logs')
    login_type = models.CharField(max_length=10, choices=LOGIN_TYPES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

class AccessAttempt(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    photo = models.ImageField(upload_to='intruders/', null=True, blank=True)
    was_successful = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Intento desde {self.ip_address} el {self.timestamp}"



class SalatQueryLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='salat_queries')
    location_name = models.CharField(max_length=255, default="Punto en el Mapa")
    latitude = models.CharField(max_length=50)
    longitude = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} consultó {self.location_name} el {self.timestamp.strftime('%d/%m/%Y')}"