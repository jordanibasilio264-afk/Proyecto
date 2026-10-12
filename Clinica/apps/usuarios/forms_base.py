"""Ubicación: apps/usuarios/forms_base.py
Utilidades compartidas por todos los formularios."""
import re

from django import forms
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db.models import Q

FORMATO_FECHA_HORA = "%Y-%m-%dT%H:%M"


class FechaInput(forms.DateInput):
    input_type = "date"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format="%Y-%m-%d")


class FechaHoraInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format=FORMATO_FECHA_HORA)


class HoraInput(forms.TimeInput):
    input_type = "time"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format="%H:%M")


class EstiloFormMixin:
    """
    - Pone clases CSS a todos los campos (form-control / form-select / form-check-input).
    - Usa calendarios y relojes HTML5 para campos de fecha, fecha-hora y hora.
    - Evita el ValueError de Django cuando model.clean() devuelve errores de un
      campo que la vista fijó y por eso no está en el formulario.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            self._preparar_campo(campo)

    @staticmethod
    def _preparar_campo(campo):
        nuevo = None
        if isinstance(campo, forms.DateTimeField):
            nuevo = FechaHoraInput()
            campo.input_formats = [FORMATO_FECHA_HORA, *campo.input_formats]
        elif isinstance(campo, forms.DateField):
            nuevo = FechaInput()
        elif isinstance(campo, forms.TimeField):
            nuevo = HoraInput()
        if nuevo is not None:
            nuevo.is_required = campo.required
            campo.widget = nuevo

        widget = campo.widget
        if isinstance(widget, forms.CheckboxInput):
            clase = "form-check-input"
        elif isinstance(widget, forms.Select):
            clase = "form-select"
        else:
            clase = "form-control"
        widget.attrs["class"] = f"{widget.attrs.get('class', 'css')} {clase}".strip()

    def _update_errors(self, errors):
        if hasattr(errors, "error_dict"):
            conocidos, extras = {}, []
            for campo, lista in errors.error_dict.items():
                if campo == NON_FIELD_ERRORS or campo in self.fields:
                    conocidos[campo] = lista
                else:
                    extras.extend(lista)
            if extras:
                conocidos.setdefault(NON_FIELD_ERRORS, []).extend(extras)
            errors = ValidationError(conocidos)
        super()._update_errors(errors)


class FiltroFechasForm(EstiloFormMixin, forms.Form):
    """Base de los formularios de búsqueda/filtrado (RF-18)."""

    desde = forms.DateField(label="Desde", required=False)
    hasta = forms.DateField(label="Hasta", required=False)

    def clean(self):
        datos = super().clean()
        desde, hasta = datos.get("desde"), datos.get("hasta")
        if desde and hasta and desde > hasta:
            raise ValidationError("La fecha «desde» no puede ser posterior a «hasta».")
        return datos

    def filtrar_fechas(self, qs, campo):
        """Filtra por un campo DateTime. Úsalo solo después de is_valid()."""
        desde, hasta = self.cleaned_data.get("desde"), self.cleaned_data.get("hasta")
        if desde:
            qs = qs.filter(**{f"{campo}__date__gte": desde})
        if hasta:
            qs = qs.filter(**{f"{campo}__date__lte": hasta})
        return qs


def buscar_texto(qs, texto, campos):
    """Cada palabra escrita debe aparecer en alguno de los campos indicados."""
    for palabra in (texto or "").split():
        condicion = Q()
        for campo in campos:
            condicion |= Q(**{f"{campo}__icontains": palabra})
        qs = qs.filter(condicion)
    return qs


def limpiar_telefono(valor):
    valor = (valor or "").strip()
    if valor and not 7 <= len(re.sub(r"\D", "", valor)) <= 15:
        raise ValidationError("Ingresa un teléfono válido.")
    return valor


def limpiar_nombre(valor):
    return " ".join((valor or "").split())