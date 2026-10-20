"""Ubicación: apps/pagos/forms.py"""
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from apps.Citas.models import Cita
from apps.SegurosMedicos.models import SeguroPaciente
from apps.usuarios.forms_base import EstiloFormMixin, FiltroFechasForm, buscar_texto
from apps.usuarios.models import Paciente

from .models import Pago


class PagoForm(EstiloFormMixin, forms.ModelForm):
    """Registrar / editar pago. Uso: PagoForm(request.POST or None, usuario=request.user, paciente=None)"""

    estado = forms.ChoiceField(
        choices=[(Pago.Estado.PAGADO, "Pagado"), (Pago.Estado.PENDIENTE, "Pendiente")],
        initial=Pago.Estado.PAGADO,
    )

    class Meta:
        model = Pago
        fields = ["paciente", "cita", "concepto", "monto", "seguro_paciente",
                  "monto_cubierto_seguro", "metodo", "estado", "fecha_pago",
                  "referencia", "observaciones"]
        labels = {"monto": "Monto total", "monto_cubierto_seguro": "Cubierto por el seguro",
                  "metodo": "Método de pago", "fecha_pago": "Fecha y hora del pago",
                  "referencia": "Referencia / No. de transacción"}
        widgets = {
        "fecha_pago": forms.DateTimeInput(
        attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }   

    def __init__(self, *args, usuario=None, paciente=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.fields["monto_cubierto_seguro"].required = False
        self.fields["monto_cubierto_seguro"].initial = Decimal("0.00")
        self.fields["monto"].widget.attrs.update({"min": "0.01", "step": "0.01"})
        self.fields["monto_cubierto_seguro"].widget.attrs.update({"min": "0", "step": "0.01"})
        self.fields["fecha_pago"].input_formats = ["%Y-%m-%dT%H:%M"]

        self.paciente_texto = ""
        if paciente is not None:
            del self.fields["paciente"]
            self.instance.paciente = paciente
            paciente_id = paciente.pk
        else:
            self.fields["paciente"].queryset = Paciente.objects.filter(activo=True)
            self.fields["paciente"].widget = forms.HiddenInput()   # <- esto quita el select
            bruto = self.data.get(self.add_prefix("paciente")) if self.is_bound else None
            paciente_id = bruto or self.instance.paciente_id

        if paciente_id and str(paciente_id).isdigit():
            p = Paciente.objects.filter(pk=paciente_id).first()
            self.paciente_texto = str(p) if p else ""
            self.fields["cita"].queryset = Cita.objects.filter(
                paciente_id=paciente_id).exclude(estado="CANCELADA")
            self.fields["seguro_paciente"].queryset = SeguroPaciente.objects.filter(
                paciente_id=paciente_id, activo=True).select_related("seguro")

        # Si ya se conoce el paciente, solo sus citas y seguros.
        if paciente_id and str(paciente_id).isdigit():
            self.fields["cita"].queryset = Cita.objects.filter(
                paciente_id=paciente_id).exclude(estado="CANCELADA")
            self.fields["seguro_paciente"].queryset = SeguroPaciente.objects.filter(
                paciente_id=paciente_id, activo=True).select_related("seguro")

        else:
            self.fields["cita"].queryset = Cita.objects.none()
            self.fields["seguro_paciente"].queryset = SeguroPaciente.objects.none()

    def clean_monto_cubierto_seguro(self):
        return self.cleaned_data.get("monto_cubierto_seguro") or Decimal("0.00")

    def clean(self):
        datos = super().clean()
        if self.instance.pk and self.instance.estado == Pago.Estado.ANULADO:
            raise ValidationError("Un pago anulado no se puede modificar.")
        paciente = datos.get("paciente") or getattr(self.instance, "paciente", None)
        cita, seguro = datos.get("cita"), datos.get("seguro_paciente")
        cubierto = datos.get("monto_cubierto_seguro") or Decimal("0")

        if paciente is not None:
            if cita and cita.paciente_id != paciente.pk:
                self.add_error("cita", "La cita pertenece a otro paciente.")
            if seguro and seguro.paciente_id != paciente.pk:
                self.add_error("seguro_paciente", "El seguro pertenece a otro paciente.")
        if cubierto > 0 and not seguro:
            self.add_error("seguro_paciente", "Indica el seguro que cubre ese monto.")
        if seguro and not seguro.vigente:
            self.add_error("seguro_paciente", "El seguro no está vigente.")
        if datos.get("metodo") in (Pago.Metodo.TARJETA, Pago.Metodo.TRANSFERENCIA, Pago.Metodo.CHEQUE) \
                and not datos.get("referencia"):
            self.add_error("referencia", "Indica la referencia del pago.")
        return datos

    def save(self, commit=True):
        pago = super().save(commit=False)
        if pago._state.adding and self.usuario is not None:
            pago.recibido_por = self.usuario
        if commit:
            pago.save()
        return pago


class AnularPagoForm(EstiloFormMixin, forms.Form):
    """Los pagos no se borran: se anulan con un motivo.
    Uso: form = AnularPagoForm(request.POST or None, pago=pago); form.guardar()"""

    motivo = forms.CharField(label="Motivo de la anulación", max_length=255,
                             widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, pago, **kwargs):
        super().__init__(*args, **kwargs)
        self.pago = pago

    def clean(self):
        datos = super().clean()
        if self.pago.estado == Pago.Estado.ANULADO:
            raise ValidationError("Este pago ya está anulado.")
        return datos

    def guardar(self):
        self.pago.anular(self.cleaned_data["motivo"])
        return self.pago


class FiltroPagoForm(FiltroFechasForm):
    q = forms.CharField(label="Buscar", required=False, widget=forms.TextInput(
        attrs={"placeholder": "No. de recibo, paciente, concepto o referencia"}))
    estado = forms.ChoiceField(required=False, choices=[("", "Todos los estados"), *Pago.Estado.choices])
    metodo = forms.ChoiceField(required=False, choices=[("", "Todos los métodos"), *Pago.Metodo.choices])
    field_order = ["q", "estado", "metodo", "desde", "hasta"]

    def filtrar(self, qs):
        datos = self.cleaned_data
        qs = buscar_texto(qs, datos.get("q"), [
            "numero_recibo", "paciente__nombres", "paciente__apellidos", "concepto", "referencia"])
        if datos.get("estado"):
            qs = qs.filter(estado=datos["estado"])
        if datos.get("metodo"):
            qs = qs.filter(metodo=datos["metodo"])
        return self.filtrar_fechas(qs, "fecha_pago")