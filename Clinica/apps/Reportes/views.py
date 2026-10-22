from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from openpyxl import Workbook
from xhtml2pdf import pisa

from apps.Citas.models import Cita
from apps.Expedientes.models import Consulta
from apps.pagos.models import Pago
from apps.usuarios.models import Medico, Paciente

from .forms import ReporteForm
from .models import ReporteGenerado


# ---------------------------------------------------------------
# Formulario: completa tipo/formato y fuerza el médico si aplica
# ---------------------------------------------------------------
def _form(request, tipo=None, formato=None):
    data = request.GET.copy()
    tipo = (tipo or data.get("tipo") or "pacientes").upper()
    if tipo == "TODOS":                      # opción "Todos los reportes" del select
        tipo = "PACIENTES"
    data["tipo"] = tipo
    data["formato"] = (formato or data.get("formato") or "pdf").upper()

    if request.user.es_medico:
        perfil = getattr(request.user, "perfil_medico", None)
        if perfil:
            data["medico"] = perfil.pk

    return ReporteForm(data, usuario=request.user)


# ---------------------------------------------------------------
# Consultas a la base de datos, filtradas por período/médico/paciente
# ---------------------------------------------------------------
def _querysets(params):
    desde, hasta = params.get("desde"), params.get("hasta")
    medico_id, paciente_id = params.get("medico_id"), params.get("paciente_id")

    def rango(qs, campo):
        if desde:
            qs = qs.filter(**{f"{campo}__date__gte": desde})
        if hasta:
            qs = qs.filter(**{f"{campo}__date__lte": hasta})
        return qs

    citas = rango(Cita.objects.select_related("paciente", "medico__usuario"), "inicio")
    pagos = rango(
        Pago.objects.select_related("paciente").exclude(estado=Pago.Estado.ANULADO),
        "fecha_pago",
    )
    consultas = Consulta.objects.select_related("expediente__paciente")   # AJUSTA: filtro de fecha
    pacientes = Paciente.objects.filter(activo=True)
    medicos = Medico.objects.filter(activo=True).select_related("usuario")

    if medico_id:
        citas = citas.filter(medico_id=medico_id)
        medicos = medicos.filter(pk=medico_id)
        # AJUSTA: consultas = consultas.filter(medico_id=medico_id)
    if paciente_id:
        citas = citas.filter(paciente_id=paciente_id)
        pagos = pagos.filter(paciente_id=paciente_id)
        consultas = consultas.filter(expediente__paciente_id=paciente_id)
        pacientes = pacientes.filter(pk=paciente_id)

    return {
        "PACIENTES": pacientes,
        "CITAS": citas,
        "CONSULTAS": consultas,
        "PAGOS": pagos,
        "MEDICOS": medicos,
    }


# ---------------------------------------------------------------
# Página principal de Reportes
# ---------------------------------------------------------------
@login_required
def reportes(request):
    form = _form(request)
    params = form.parametros() if form.is_valid() else {}
    q = _querysets(params)

    ingresos = (
        q["PAGOS"].filter(estado=Pago.Estado.PAGADO).aggregate(t=Sum("monto"))["t"] or 0
    )

    return render(request, "reportes.html", {
        "form": form,
        "pacientes": q["PACIENTES"].count(),
        "citas": q["CITAS"].count(),
        "consultas": q["CONSULTAS"].count(),
        "pagos": q["PAGOS"].count(),
        "diagnosticos": 0,                      # AJUSTA cuando tengas el modelo
        "medicos": q["MEDICOS"].count(),
        "ingresos": f"RD${ingresos:,.2f}",
    })


# ---------------------------------------------------------------
# Columnas de cada reporte: (encabezados, función que arma la fila)
# ---------------------------------------------------------------
def _local(dt):
    return timezone.localtime(dt).strftime("%d/%m/%Y %H:%M")


COLUMNAS = {
    "PACIENTES": (
        ["Nombres", "Apellidos", "Cédula"],
        lambda p: [p.nombres, p.apellidos, getattr(p, "cedula", "")],
    ),
    "CITAS": (
        ["Paciente", "Médico", "Fecha", "Duración (min)", "Estado", "Motivo"],
        lambda c: [str(c.paciente), str(c.medico), _local(c.inicio),
                   c.duracion_minutos, c.get_estado_display(), c.motivo],
    ),
    "PAGOS": (
        ["Recibo", "Paciente", "Concepto", "Monto", "Método", "Estado", "Fecha"],
        lambda p: [p.numero_recibo, str(p.paciente), p.concepto, float(p.monto),
                   p.get_metodo_display(), p.get_estado_display(), _local(p.fecha_pago)],
    ),
    "MEDICOS": (
        ["Médico", "Especialidades"],
        lambda m: [str(m), ", ".join(e.nombre for e in m.especialidades.all())],
    ),
    "CONSULTAS": (
        ["Paciente"],                                    # AJUSTA: agrega fecha, médico, etc.
        lambda c: [str(c.expediente.paciente)],
    ),
}


# ---------------------------------------------------------------
# Descarga: /reportes/exportar/<tipo>/<formato>/?desde=...&hasta=...
# ---------------------------------------------------------------
@login_required
def generar(request, tipo, formato):
    form = _form(request, tipo, formato)
    if not form.is_valid():
        return HttpResponse(f"Parámetros inválidos: {form.errors.as_text()}", status=400)

    params = form.parametros()
    tipo, formato = params["tipo"], form.cleaned_data["formato"]

    if tipo not in COLUMNAS:
        return HttpResponse("Este reporte aún no está disponible.", status=400)

    encabezados, fila = COLUMNAS[tipo]
    qs = _querysets(params)[tipo]
    if tipo == "MEDICOS":
        qs = qs.prefetch_related("especialidades")

    ReporteGenerado.objects.create(
        tipo=tipo, formato=formato, parametros=params, generado_por=request.user
    )

    if formato == "EXCEL":
        wb = Workbook()
        ws = wb.active
        ws.title = tipo.title()
        ws.append(encabezados)
        for obj in qs:
            ws.append(fila(obj))
        resp = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        resp["Content-Disposition"] = f'attachment; filename="reporte_{tipo.lower()}.xlsx"'
        wb.save(resp)
        return resp

    return _pdf(request, tipo, encabezados, [fila(o) for o in qs], params)


def _pdf(request, tipo, encabezados, filas, params):
    html = render_to_string("reportes_pdf.html", {
        "titulo": f"Reporte de {tipo.title()}",
        "encabezados": encabezados,
        "filas": filas,
        "desde": params.get("desde"),
        "hasta": params.get("hasta"),
        "generado_por": request.user,
        "fecha": timezone.localtime(),
    })
    resp = HttpResponse(content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="reporte_{tipo.lower()}.pdf"'
    resultado = pisa.CreatePDF(html, dest=resp, encoding="utf-8")
    if resultado.err:
        return HttpResponse("Error al generar el PDF", status=500)
    return resp