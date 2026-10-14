from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Paciente


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil_paciente(sender, instance, **kwargs):
    if instance.rol == "PACIENTE":
        Paciente.objects.get_or_create(
            usuario=instance,
            defaults={
                "nombres": instance.first_name or instance.email,
                "apellidos": instance.last_name,
                "email": instance.email,
                "telefono": instance.telefono,
            },
        )