"""Ubicación: apps/Documentos/views.py
Página + API JSON para consultas médicas y documentos del paciente."""
import json
import re
from functools import wraps
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.http import require_GET, require_POST

from apps.Expedientes.models import Consulta, Expediente
from apps.usuarios.models import Paciente,Medico

from .models import Documento

PA_RE = re.compile(r"\s*(\d{2,3})\s*/\s*(\d{2,3})\s*")


# ---------- helpers ----------
def _errores(exc):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return {"__all__": exc.messages}


def _bad(errores, status=400):
    return JsonResponse({"errores": errores}, status=status)


def _json_errors(view):
    """En desarrollo (DEBUG) un fallo inesperado devuelve su causa en JSON,
    para verla en el toast. En producción se relanza el error normal."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except (Http404, PermissionDenied):
            raise
        except Exception as e:
            if settings.DEBUG:
                return _bad({"__all__": [f"{type(e).__name__}: {e}"]}, 500)
            raise
    return wrapper


def _int(valor, campo):
    if valor in (None, ""):
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise ValidationError({campo: "Debe ser un número entero."})


def _dec(valor, campo):
    if valor in (None, ""):
        return None
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        raise ValidationError({campo: "Debe ser un número."})


def _consulta_json(c):
    pa = ""
    if c.presion_sistolica and c.presion_diastolica:
        pa = f"{c.presion_sistolica}/{c.presion_diastolica}"
    return {
        "id": c.pk,
        "fecha": timezone.localtime(c.fecha).isoformat(),
        "motivo": c.motivo_consulta,
        "diagnostico": c.diagnostico,
        "tratamiento": c.tratamiento,
        "observaciones": c.observaciones,
        "enfermedad_actual": c.enfermedad_actual,
        "requiere_seguimiento": c.requiere_seguimiento,
        "fecha_seguimiento": c.fecha_seguimiento.isoformat() if c.fecha_seguimiento else None,
        "medico": str(c.medico),
        "vitales": {
            "pa": pa,
            "fc": c.frecuencia_cardiaca,
            "temp": str(c.temperatura) if c.temperatura is not None else None,
            "fr": c.frecuencia_respiratoria,
            "sat": c.saturacion_oxigeno,
            "peso": str(c.peso_kg) if c.peso_kg is not None else None,
        },
    }


def _documento_json(d):
    return {
        "id": d.pk,
        "titulo": d.titulo,
        "tipo": d.get_tipo_display(),
        "descripcion": d.descripcion,
        "tam": d.tamano_bytes,
        "consulta_id": d.consulta_id,
        "fecha": timezone.localtime(d.creado_en).isoformat(),
        "url": reverse("documento_descargar", args=[d.pk]),
    }


# ---------- página ----------
@login_required
def documentos_page(request):
    pacientes = Paciente.objects.all().order_by("apellidos", "nombres")
    return render(request, "documentos.html", {"pacientes": pacientes})


# ---------- consultas ----------
@login_required
@_json_errors
def consultas_api(request, paciente_id):
    """GET: lista las consultas del paciente. POST: crea una consulta."""
    paciente = get_object_or_404(Paciente, pk=paciente_id)

    if request.method == "GET":
        consultas = (
            Consulta.objects.filter(expediente__paciente=paciente)
            .select_related("medico", "expediente__paciente")
            .order_by("-fecha")
        )
        return JsonResponse({"consultas": [_consulta_json(c) for c in consultas]})

    if request.method != "POST":
        return JsonResponse({"errores": {"__all__": ["Método no permitido."]}}, status=405)

    # Solo un médico registra consultas (se toma del usuario autenticado).
    medico = Medico.objects.filter(usuario=request.user).first()
    if medico is None:
        return _bad({"__all__": ["Solo un usuario con rol Médico puede registrar consultas."]}, 403)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _bad({"__all__": ["JSON inválido."]})

    try:
        motivo = (data.get("motivo") or "").strip()
        diagnostico = (data.get("diagnostico") or "").strip()
        errores = {}
        if not motivo:
            errores["motivo_consulta"] = "El motivo es obligatorio."
        if not diagnostico:
            errores["diagnostico"] = "El diagnóstico es obligatorio."

        fecha = parse_datetime(data.get("fecha") or "") or timezone.now()
        if timezone.is_naive(fecha):
            fecha = timezone.make_aware(fecha)

        sistolica = diastolica = None
        pa = (data.get("presion") or "").strip()
        if pa:
            m = PA_RE.fullmatch(pa)
            if not m:
                errores["presion_sistolica"] = "Usa el formato 120/80."
            else:
                sistolica, diastolica = int(m.group(1)), int(m.group(2))

        requiere = bool(data.get("requiere_seguimiento"))
        fecha_seg = None
        if requiere and data.get("fecha_seguimiento"):
            try:
                fecha_seg = parse_date(data["fecha_seguimiento"])
            except ValueError:
                fecha_seg = None
            if fecha_seg is None:
                errores["fecha_seguimiento"] = "Fecha de seguimiento inválida."
        elif requiere:
            errores["fecha_seguimiento"] = "Indica la fecha de seguimiento."

        if errores:
            raise ValidationError(errores)

        with transaction.atomic():
            expediente, _ = Expediente.objects.get_or_create(paciente=paciente)
            consulta = Consulta(
                expediente=expediente,
                medico=medico,
                fecha=fecha,
                motivo_consulta=motivo,
                diagnostico=diagnostico,
                tratamiento=(data.get("tratamiento") or "").strip(),
                observaciones=(data.get("observaciones") or "").strip(),
                presion_sistolica=sistolica,
                presion_diastolica=diastolica,
                frecuencia_cardiaca=_int(data.get("fc"), "frecuencia_cardiaca"),
                temperatura=_dec(data.get("temp"), "temperatura"),
                frecuencia_respiratoria=_int(data.get("fr"), "frecuencia_respiratoria"),
                saturacion_oxigeno=_int(data.get("sat"), "saturacion_oxigeno"),
                peso_kg=_dec(data.get("peso"), "peso_kg"),
                enfermedad_actual=(data.get("enfermedad_actual") or "").strip(),
                requiere_seguimiento=requiere,
                fecha_seguimiento=fecha_seg,
            )
            consulta.full_clean()
            consulta.save()
    except ValidationError as e:
        return _bad(_errores(e))

    return JsonResponse({"consulta": _consulta_json(consulta)}, status=201)


# ---------- documentos ----------
@login_required
@_json_errors
def documentos_api(request, paciente_id):
    """GET: lista documentos activos del paciente. POST: sube uno."""
    paciente = get_object_or_404(Paciente, pk=paciente_id)

    if request.method == "GET":
        docs = Documento.objects.filter(paciente=paciente, activo=True)
        return JsonResponse({"documentos": [_documento_json(d) for d in docs]})

    if request.method != "POST":
        return JsonResponse({"errores": {"__all__": ["Método no permitido."]}}, status=405)

    archivo = request.FILES.get("archivo")
    if not archivo:
        return _bad({"archivo": ["Selecciona un archivo."]})

    tipo = request.POST.get("tipo") or Documento.Tipo.OTRO
    descripcion = (request.POST.get("descripcion") or "").strip()
    titulo = (request.POST.get("titulo") or "").strip() or archivo.name[:150]

    # Consulta asociada (opcional): debe pertenecer al mismo paciente.
    consulta = None
    cid = (request.POST.get("consulta") or "").strip()
    if cid:
        if cid.isdigit():
            consulta = Consulta.objects.filter(pk=cid, expediente__paciente=paciente).first()
        if consulta is None:
            return _bad({"consulta": ["La consulta no pertenece a este paciente."]})

    doc = Documento(
        paciente=paciente,
        titulo=titulo,
        tipo=tipo,
        archivo=archivo,
        descripcion=descripcion,
        consulta=consulta,
        subido_por=request.user,
    )
    try:
        doc.full_clean()
    except ValidationError as e:
        return _bad(_errores(e))
    try:
        doc.save()
    except Exception as e:  # en desarrollo, muestra la causa real en el toast
        if settings.DEBUG:
            return _bad({"__all__": [f"{type(e).__name__}: {e}"]}, 500)
        raise
    return JsonResponse({"documento": _documento_json(doc)}, status=201)


@login_required
@require_POST
@_json_errors
def documento_desactivar(request, pk):
    """'Eliminar' = desactivar (los datos médicos no se borran)."""
    doc = get_object_or_404(Documento, pk=pk, activo=True)
    doc.activo = False
    doc.save(update_fields=["activo"])
    return JsonResponse({"ok": True})


@login_required
@require_GET
def documento_descargar(request, pk):
    """Sirve el archivo solo a usuarios autenticados (no por URL pública de MEDIA)."""
    doc = get_object_or_404(Documento, pk=pk, activo=True)
    try:
        return FileResponse(doc.archivo.open("rb"), as_attachment=False)
    except FileNotFoundError:
        raise Http404("Archivo no encontrado.")

def rol_requerido(*roles):
    def decorador(vista):
        @wraps(vista)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            if request.user.rol not in roles:   # ajusta a como guardas el rol
                raise PermissionDenied 
            return vista(request, *args, **kwargs)
        return wrapper
    return decorador


@rol_requerido("ADMIN", "RECEPCIONISTA", "MEDICO","PACIENTE")
def documentos(request):
    pacientes = Paciente.objects.order_by("apellidos", "nombres")
    return render(request, "documentos.html", {"pacientes": pacientes})