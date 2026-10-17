from datetime import date
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from xhtml2pdf import pisa

from apps.Documentos.forms import DocumentoForm
from apps.Documentos.models import Documento
from apps.usuarios.models import Paciente
from .forms import ExpedienteForm
from .models import Expediente


def requiere_permiso(codigo):
    """Login + permiso por rol (PERMISOS_POR_ROL)."""
    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            if not request.user.tiene_permiso(codigo):
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


# ---------- Consultar (lista + búsqueda) ----------
@requiere_permiso("expedientes.ver")
def lista_expedientes(request):
    query = request.GET.get("q", "").strip()
    qs = (Expediente.objects.select_related("paciente")
          .annotate(docs_activos=Count(
              "paciente__documentos",
              filter=Q(paciente__documentos__activo=True), distinct=True))
          .order_by("-actualizado_en"))
    if query:
        qs = qs.filter(
            Q(numero__icontains=query)
            | Q(paciente__nombres__icontains=query)
            | Q(paciente__apellidos__icontains=query))

    pagina = Paginator(qs, 15).get_page(request.GET.get("page"))

    return render(request, "expedientes.html", {
        "expedientes": pagina,
        "pagina": pagina,
        "query": query,
        "pacientes": Paciente.objects.filter(activo=True, expediente__isnull=True),
        "today_date": timezone.localdate().isoformat(),
    })


# ---------- Crear ----------
@requiere_permiso("expedientes.crear")
@require_POST
def crear_expediente(request):
    p = request.POST
    paciente_id = p.get("paciente_id", "").strip()

    if not paciente_id.isdigit():
        messages.error(request, "Seleccione un paciente de la lista.")
        return redirect("expedientes")

    paciente = Paciente.objects.filter(pk=paciente_id).first()
    if paciente is None:
        messages.error(request, "El paciente seleccionado no existe.")
        return redirect("expedientes")

    if Expediente.objects.filter(paciente=paciente).exists():
        messages.error(request, "Este paciente ya tiene un expediente.")
        return redirect("expedientes")

    try:
        with transaction.atomic():
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

            cedula = p.get("cedula", "").strip()
            if cedula:
                paciente.cedula = cedula

            campos_texto = {
                "telefono": "telefono",
                "direccion": "direccion",
                "contacto_emergencia_nombre": "nombre_contacto",
                "contacto_emergencia_telefono": "telefono_contacto",
            }
            for campo, nombre_post in campos_texto.items():
                valor = p.get(nombre_post, "").strip()
                if valor:
                    setattr(paciente, campo, valor)

            paciente.full_clean()
            paciente.save()

            Expediente.objects.create(
                paciente=paciente,
                fecha_apertura=p.get("fecha_apertura") or date.today(),
                alergias=p.get("alergias", ""),
                antecedentes_personales=p.get("antecedentes", ""),
                antecedentes_familiares=p.get("antecedentes_familiares", ""),
                cirugias_previas=p.get("cirugias_previas", ""),
                observaciones_generales=p.get("observaciones", ""),
                tratamientos=p.get("tratamientos", ""),
            )

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


# ---------- Consultar detalle + historial médico + documentos ----------
@requiere_permiso("expedientes.ver")
def detalle_expediente(request, pk):
    exp = get_object_or_404(Expediente.objects.select_related("paciente"), pk=pk)
    consultas = (exp.consultas.select_related("medico__usuario")
                 .order_by("-fecha"))
    pagina = Paginator(consultas, 10).get_page(request.GET.get("page"))
    documentos = exp.paciente.documentos.filter(activo=True)
    return render(request, "detalle_expediente.html", {
        "exp": exp,
        "pagina": pagina,
        "documentos": documentos,
        "form_doc": DocumentoForm(usuario=request.user, paciente=exp.paciente),
    })


# ---------- Actualizar ----------
@requiere_permiso("expedientes.editar")
def editar_expediente(request, pk):
    exp = get_object_or_404(Expediente.objects.select_related("paciente"), pk=pk)
    form = ExpedienteForm(request.POST or None, instance=exp)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Expediente actualizado correctamente.")
        return redirect("detalle_expediente", pk=exp.pk)
    return render(request, "editar_expediente.html",
                  {"exp": exp, "form": form})


# ---------- Adjuntar documentos ----------
@requiere_permiso("documentos.subir")
@require_POST
def adjuntar_documento(request, pk):
    exp = get_object_or_404(Expediente.objects.select_related("paciente"), pk=pk)
    form = DocumentoForm(request.POST, request.FILES,
                         usuario=request.user, paciente=exp.paciente)
    if form.is_valid():
        form.save()
        messages.success(request, "Documento adjuntado correctamente.")
    else:
        errores = "; ".join(e for lista in form.errors.values() for e in lista)
        messages.error(request, f"No se pudo adjuntar: {errores}")
    return redirect("detalle_expediente", pk=exp.pk)


# ---------- Descargar PDF ----------
@requiere_permiso("expedientes.descargar_pdf")
def descargar_expediente_pdf(request, pk):
    exp = get_object_or_404(Expediente.objects.select_related("paciente"), pk=pk)
    html = get_template("expediente_pdf.html").render({
        "exp": exp,
        "consultas": exp.consultas.select_related("medico__usuario").order_by("-fecha"),
        "documentos": exp.paciente.documentos.filter(activo=True),
        "generado": timezone.localtime(),
        "generado_por": request.user,
    })
    respuesta = HttpResponse(content_type="application/pdf")
    respuesta["Content-Disposition"] = f'attachment; filename="{exp.numero or "expediente"}.pdf"'
    resultado = pisa.CreatePDF(html, dest=respuesta, encoding="utf-8")
    if resultado.err:
        return HttpResponse("No se pudo generar el PDF.", status=500)
    return respuesta