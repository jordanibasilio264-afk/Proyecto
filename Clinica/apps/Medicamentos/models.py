"""Ubicación: apps/Medicamentos/models.py
Incluye: Medicamento (RF-11), Receta y DetalleReceta (RF-10)."""
from django.db import models
from django.utils import timezone

from apps.usuarios.base import ModeloBase, NoEliminable


class Medicamento(ModeloBase):
    class Forma(models.TextChoices):
        TABLETA = "TABLETA", "Tableta"
        CAPSULA = "CAPSULA", "Cápsula"
        JARABE = "JARABE", "Jarabe / suspensión"
        INYECCION = "INYECCION", "Inyección"
        CREMA = "CREMA", "Crema / ungüento"
        GOTAS = "GOTAS", "Gotas"
        INHALADOR = "INHALADOR", "Inhalador"
        OTRA = "OTRA", "Otra"

    nombre_comercial = models.CharField(max_length=150, db_index=True)
    nombre_generico = models.CharField(max_length=150, db_index=True)
    concentracion = models.CharField(max_length=50, blank=True)  # ej. 500 mg
    forma = models.CharField(max_length=15, choices=Forma.choices, default=Forma.TABLETA)
    laboratorio = models.CharField(max_length=100, blank=True)
    indicaciones = models.TextField(blank=True)
    contraindicaciones = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre_comercial"]
        constraints = [
            models.UniqueConstraint(
                fields=["nombre_comercial", "concentracion", "forma"],
                name="medicamento_unico",
            )
        ]
        verbose_name = "medicamento"
        verbose_name_plural = "medicamentos"

    def __str__(self):
        extra = f" {self.concentracion}" if self.concentracion else ""
        return f"{self.nombre_comercial}{extra} ({self.nombre_generico})"


class Receta(NoEliminable):
    """Receta emitida durante una consulta. No se elimina."""

    consulta = models.ForeignKey(
        "Expedientes.Consulta", on_delete=models.PROTECT, related_name="recetas"
    )
    numero = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    fecha = models.DateTimeField(default=timezone.now)
    indicaciones_generales = models.TextField(blank=True)
    vigente_hasta = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "receta"
        verbose_name_plural = "recetas"

    def __str__(self):
        return f"{self.numero or 'RX'} - {self.paciente}"

    @property
    def paciente(self):
        return self.consulta.expediente.paciente

    @property
    def medico(self):
        return self.consulta.medico

    def save(self, *args, **kwargs):
        nuevo = self._state.adding
        super().save(*args, **kwargs)
        if nuevo and not self.numero:
            self.numero = f"RX-{self.pk:06d}"
            type(self).objects.filter(pk=self.pk).update(numero=self.numero)


class DetalleReceta(ModeloBase):
    receta = models.ForeignKey(Receta, on_delete=models.CASCADE, related_name="detalles")
    medicamento = models.ForeignKey(
        Medicamento, on_delete=models.PROTECT, related_name="usos_en_recetas"
    )
    dosis = models.CharField(max_length=100)          # ej. 1 tableta
    frecuencia = models.CharField(max_length=100)     # ej. cada 8 horas
    duracion_dias = models.PositiveSmallIntegerField(null=True, blank=True)
    via_administracion = models.CharField(max_length=50, blank=True)
    cantidad = models.PositiveSmallIntegerField(default=1)
    instrucciones = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["receta", "medicamento"], name="medicamento_unico_por_receta"
            )
        ]
        verbose_name = "detalle de receta"
        verbose_name_plural = "detalles de receta"

    def __str__(self):
        return f"{self.medicamento} - {self.dosis} {self.frecuencia}"