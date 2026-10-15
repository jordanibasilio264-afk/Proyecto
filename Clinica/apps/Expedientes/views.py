from functools import wraps
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from apps.Documentos.forms import DocumentoForm
from .forms import ExpedienteForm
from .models import Expediente
from apps.usuarios.models import Paciente


def rol_requerido(*roles):
    def decorador(vista):
        @wraps(vista)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            if request.user.rol not in roles:
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return wrapper
    return decorador


@rol_requerido("ADMIN", "RECEPCIONISTA", "MEDICO")
def expedientes(request):
    q = request.GET.get("q", "").strip()

    lista = Expediente.objects.select_related("paciente")
    if q:
        lista = lista.filter(
            Q(codigo__icontains=q)
            | Q(paciente__nombres__icontains=q)
            | Q(paciente__apellidos__icontains=q)
        )

    pacientes = Paciente.objects.filter(activo=True).order_by("apellidos", "nombres")

    return render(request, "expedientes.html", {
        "expedientes": lista,
        "pacientes": pacientes,
        "query": q,
        "today_date": timezone.localdate().isoformat(),
    })


@rol_requerido("ADMIN", "RECEPCIONISTA", "MEDICO")
def crear_expediente(request):
    if request.method == "POST":
        paciente = get_object_or_404(Paciente, pk=request.POST.get("paciente"))
        Expediente.objects.create(
            paciente=paciente,
            alergias=request.POST.get("alergias", ""),
            fecha_apertura=request.POST.get("fecha_apertura", None),
            antecedentes_personales=request.POST.get("antecedentes", ""),
            # agrega aquí los demás campos de tu modelo Expediente
        )
        messages.success(request, "Expediente creado.")
    return redirect("expedientes")

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
        "expedientes": pagina,   # ahora es la página actual
        "pagina": pagina,
        "query": query,
        "pacientes": Paciente.objects.filter(activo=True, expediente__isnull=True),
        "today_date": timezone.localdate().isoformat(),
    })


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