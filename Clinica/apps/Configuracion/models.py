"""Ubicación: apps/Configuracion/models.py"""
from django.core.exceptions import PermissionDenied
from django.core.validators import FileExtensionValidator
from django.db import models
from django.conf import settings

from apps.usuarios.base import ModeloBase


class ConfiguracionConsultorio(ModeloBase):
    """Registro único (singleton) con los datos y parámetros del consultorio."""

    nombre_consultorio = models.CharField(max_length=150, default="Mi consultorio")
    rnc = models.CharField("RNC", max_length=20, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    logo = models.FileField(
        upload_to="configuracion/",
        blank=True,
        validators=[FileExtensionValidator(["png", "jpg", "jpeg", "svg"])],
    )
    moneda = models.CharField(max_length=5, default="DOP")

    # Agenda
    hora_apertura = models.TimeField(default="08:00")
    hora_cierre = models.TimeField(default="17:00")
    duracion_cita_defecto = models.PositiveSmallIntegerField("duración de cita (min)", default=30)

    # Notificaciones e inteligencia (RF-15, RF-20)
    recordatorio_horas_antes = models.PositiveSmallIntegerField(default=24)
    paciente_frecuente_min_citas = models.PositiveSmallIntegerField(default=5)
    dias_alerta_seguimiento = models.PositiveSmallIntegerField(default=3)

    # Acceso
    permitir_registro_publico = models.BooleanField(default=True)

    class Meta:
        verbose_name = "configuración del consultorio"
        verbose_name_plural = "configuración del consultorio"

    def __str__(self):
        return self.nombre_consultorio

    def save(self, *args, **kwargs):
        self.pk = 1  # siempre un solo registro
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("La configuración no puede eliminarse.")

    @classmethod
    def obtener(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    from django.conf import settings

NOTIF_POR_ROL = {
    "ADMIN": ["recordatorios", "alertas", "cambios", "resumen"],
    "PACIENTE": ["recordatorios", "recetas", "cambios", "promociones"],
    "MEDICO": ["nueva_cita", "cambios", "sala_espera", "resumen"],
    "RECEPCIONISTA": ["solicitudes", "cambios", "pagos", "resumen"],
}
NOTIF_APAGADAS = {"resumen", "promociones"}


class PreferenciasUsuario(ModeloBase):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name="preferencias")
    notificaciones = models.JSONField(default=dict, blank=True)
    medio_aviso = models.CharField(max_length=15, default="correo")  # notificacion/correo/sms
    idioma = models.CharField(max_length=10, default="Español")
    zona_horaria = models.CharField(max_length=50, default="America/Santo_Domingo")
    formato_fecha = models.CharField(max_length=15, default="DD/MM/AAAA")
    vista_agenda = models.CharField(max_length=10, default="Semana")

    @classmethod
    def obtener(cls, usuario):
        obj, _ = cls.objects.get_or_create(usuario=usuario)
        for k in NOTIF_POR_ROL.get(usuario.rol, []):
            obj.notificaciones.setdefault(k, k not in NOTIF_APAGADAS)
        return obj