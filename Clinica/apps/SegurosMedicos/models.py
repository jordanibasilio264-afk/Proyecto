from django.db import models


class Seguro(models.Model):
    nombre = models.CharField(max_length=100)
    numero = models.CharField(max_length=50)
    telefono = models.CharField(max_length=20)
    estado = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre