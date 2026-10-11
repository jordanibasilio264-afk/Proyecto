"""Ubicación: apps/pagos/models.py"""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.usuarios.base import NoEliminable


class Pago(NoEliminable):
    """Pago/cobro con número de recibo. No se borra: se ANULA."""

    class Metodo(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo"
        TARJETA = "TARJETA", "Tarjeta"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        CHEQUE = "CHEQUE", "Cheque"
        SEGURO = "SEGURO", "Seguro médico"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PAGADO = "PAGADO", "Pagado"
        ANULADO = "ANULADO", "Anulado"

    numero_recibo = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    paciente = models.ForeignKey(
        "usuarios.Paciente", on_delete=models.PROTECT, related_name="pagos"
    )
    cita = models.ForeignKey(
        "Citas.Cita", on_delete=models.SET_NULL, null=True, blank=True, related_name="pagos"
    )
    concepto = models.CharField(max_length=200)
    monto = models.DecimalField(
        "monto total", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    seguro_paciente = models.ForeignKey(
        "SegurosMedicos.SeguroPaciente", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="pagos",
    )
    monto_cubierto_seguro = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    metodo = models.CharField(max_length=15, choices=Metodo.choices, default=Metodo.EFECTIVO)
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.PAGADO, db_index=True
    )
    fecha_pago = models.DateTimeField(default=timezone.now, db_index=True)
    referencia = models.CharField("referencia / No. de transacción", max_length=60, blank=True)
    observaciones = models.CharField(max_length=255, blank=True)
    recibido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="pagos_recibidos",
    )
    motivo_anulacion = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-fecha_pago"]
        verbose_name = "pago"
        verbose_name_plural = "pagos"

    def __str__(self):
        return f"{self.numero_recibo or 'REC'} - {self.paciente} - {self.monto}"

    @property
    def monto_paciente(self):
        """Lo que realmente paga el paciente."""
        return self.monto - self.monto_cubierto_seguro

    def clean(self):
        if self.monto_cubierto_seguro and self.monto_cubierto_seguro > self.monto:
            raise ValidationError({"monto_cubierto_seguro": "No puede superar el monto total."})

    def anular(self, motivo):
        self.estado = self.Estado.ANULADO
        self.motivo_anulacion = motivo
        self.save()

    def save(self, *args, **kwargs):
        nuevo = self._state.adding
        super().save(*args, **kwargs)
        if nuevo and not self.numero_recibo:
            self.numero_recibo = f"REC-{self.pk:06d}"
            type(self).objects.filter(pk=self.pk).update(numero_recibo=self.numero_recibo)