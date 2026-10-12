"""Ubicación: apps/Documentos/forms.py"""
from django import forms
from django.core.exceptions import ValidationError

from apps.Expedientes.models import Consulta
from apps.usuarios.forms_base import EstiloFormMixin, buscar_texto

from .models import MAX_MB, Documento


class DocumentoForm(EstiloFormMixin, forms.ModelForm):
    """Subir documento. Uso: DocumentoForm(request.POST or None, request.FILES or None,
                                          usuario=request.user, paciente=paciente)
    (el <form> debe llevar enctype="multipart/form-data")"""

    class Meta:
        model = Documento
        fields = ["paciente", "consulta", "titulo", "tipo", "archivo", "descripcion"]
        labels = {"titulo": "Título", "archivo": "Archivo", "descripcion": "Descripción"}

    def __init__(self, *args, usuario=None, paciente=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        archivo = self.fields["archivo"]
        archivo.widget.attrs["accept"] = ".pdf,.jpg,.jpeg,.png,.doc,.docx"
        archivo.help_text = f"PDF, JPG, PNG o Word. Máximo {MAX_MB} MB."
        if paciente is not None:
            del self.fields["paciente"]
            self.instance.paciente = paciente
            self.fields["consulta"].queryset = Consulta.objects.filter(
                expediente__paciente=paciente)
        self.fields["consulta"].required = False

    def clean(self):
        datos = super().clean()
        paciente = datos.get("paciente") or getattr(self.instance, "paciente", None)
        consulta = datos.get("consulta")
        if paciente is not None and consulta and consulta.expediente.paciente_id != paciente.pk:
            self.add_error("consulta", "La consulta pertenece a otro paciente.")
        return datos

    def save(self, commit=True):
        doc = super().save(commit=False)
        if doc._state.adding and self.usuario is not None:
            doc.subido_por = self.usuario
        if commit:
            doc.save()
        return doc


class FiltroDocumentoForm(EstiloFormMixin, forms.Form):
    q = forms.CharField(label="Buscar", required=False, widget=forms.TextInput(
        attrs={"placeholder": "Título, paciente o descripción"}))
    tipo = forms.ChoiceField(required=False, choices=[("", "Todos los tipos"), *Documento.Tipo.choices])

    def filtrar(self, qs):
        qs = buscar_texto(qs, self.cleaned_data.get("q"), [
            "titulo", "paciente__nombres", "paciente__apellidos", "descripcion"])
        if self.cleaned_data.get("tipo"):
            qs = qs.filter(tipo=self.cleaned_data["tipo"])
        return qs