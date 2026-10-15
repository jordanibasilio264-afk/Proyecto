from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from apps.Documentos.models import Documento
from apps.usuarios.models import Paciente
from .models import Expediente


@login_required
@require_POST
def crear_expediente(request):
    p = request.POST
    paciente = get_object_or_404(Paciente, pk=p.get("paciente_id"))

    if Expediente.objects.filter(paciente=paciente).exists():
        messages.error(request, "Este paciente ya tiene un expediente.")
        return redirect("expedientes")

    try:
        with transaction.atomic():
            # 1) Datos que viven en Paciente  <-- AQUÍ va el bloque nuevo
            sexo = p.get("sexo", "")
            sangre = p.get("tipo_sangre", "")
            nacimiento = parse_date(p.get("fecha_nacimiento", "") or "")

            if sexo in Paciente.Sexo.values:
                paciente.sexo = sexo
            if sangre in Paciente.TipoSangre.values:
                paciente.tipo_sangre = sangre
            if nacimiento:
                if nacimiento > date.today():
                    raise ValidationError("La fecha de nacimiento no puede ser futura.")
                paciente.fecha_nacimiento = nacimiento
            paciente.save()

            # 2) Expediente
            Expediente.objects.create(
                paciente=paciente,
                fecha_apertura=p.get("fecha_apertura") or date.today(),
                alergias=p.get("alergias", ""),
                antecedentes_personales=p.get("antecedentes", ""),
                antecedentes_familiares=p.get("antecedentes_familiares", ""),
                cirugias_previas=p.get("cirugias", ""),
                observaciones_generales=p.get("observaciones", ""),
                tratamientos=p.get("tratamientos", ""),
            )

            # 3) Archivos -> Documento
            for f in request.FILES.getlist("archivos"):
                doc = Documento(
                    paciente=paciente,
                    titulo=f.name[:150],
                    archivo=f,
                    subido_por=request.user,
                )
                doc.full_clean()
                doc.save()

    except ValidationError as e:
        messages.error(request, "; ".join(e.messages))
        return redirect("expedientes")

    messages.success(request, "Expediente creado correctamente.")
    return redirect("expedientes")