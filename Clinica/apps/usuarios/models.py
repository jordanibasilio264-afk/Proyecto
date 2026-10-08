from django.db import models
from django.contrib.auth.models import AbstractUser 

class Usuarios (AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        Medico = 'MEDICO', 'Médico'
        PACIENTE = 'PACIENTE', 'Paciente'
        Recepcionista = 'RECEPCIONISTA', 'Recepcionista'

    rol = models.CharField(max_length=20, choices=Roles.choices, default=Roles.PACIENTE,)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email

    
