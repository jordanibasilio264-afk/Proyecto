
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import FiltroMedicamentoForm, MedicamentoForm
from .models import Medicamento


def permiso_requerido(codigo):
    def decorador(vista):
        @login_required
        def wrapper(request, *args, **kwargs):
            if not request.user.tiene_permiso(codigo):
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        wrapper.__name__ = vista.__name__
        wrapper.__doc__ = vista.__doc__
        return wrapper
    return decorador


@permiso_requerido("medicamentos.ver")
def medicamentos_view(request):
    filtro = FiltroMedicamentoForm(request.GET or None)
    medicamentos = Medicamento.objects.order_by("id")

    if filtro.is_valid():
        medicamentos = filtro.filtrar(medicamentos)

    contexto = {
        "filtro": filtro,
        "medicamentos": medicamentos,
        "total_medicamentos": Medicamento.objects.count(),
        "total_activos": Medicamento.objects.filter(activo=True).count(),
        "total_inactivos": Medicamento.objects.filter(activo=False).count(),
        "puede_crear": request.user.tiene_permiso("medicamentos.crear"),
        "puede_editar": request.user.tiene_permiso("medicamentos.editar"),
        "puede_cambiar_estado": request.user.tiene_permiso(
            "medicamentos.eliminar"
        ),
    }
    return render(request, "medicamentos.html", contexto)


@permiso_requerido("medicamentos.crear")
def crear_medicamento(request):
    if request.method == "POST":
        formulario = MedicamentoForm(request.POST)
        if formulario.is_valid():
            try:
                formulario.save()
            except Exception as error:
                from django.db import IntegrityError

                if isinstance(error, IntegrityError):
                    formulario.add_error(
                        None,
                        "Ya existe un medicamento con ese nombre, "
                        "concentración y forma farmacéutica.",
                    )
                else:
                    raise
            else:
                messages.success(request, "Medicamento registrado correctamente.")
                return redirect("medicamentos")
    else:
        formulario = MedicamentoForm()

    return render(
        request,
        "formulario_medicamento.html",
        {"formulario": formulario, "modo": "crear"},
    )


@permiso_requerido("medicamentos.editar")
def editar_medicamento(request, medicamento_id):
    medicamento = get_object_or_404(Medicamento, pk=medicamento_id)

    if request.method == "POST":
        formulario = MedicamentoForm(
            request.POST,
            instance=medicamento,
        )
        if formulario.is_valid():
            try:
                formulario.save()
            except Exception as error:
                from django.db import IntegrityError

                if isinstance(error, IntegrityError):
                    formulario.add_error(
                        None,
                        "Ya existe otro medicamento con ese nombre, "
                        "concentración y forma farmacéutica.",
                    )
                else:
                    raise
            else:
                messages.success(request, "Medicamento actualizado correctamente.")
                return redirect("medicamentos")
    else:
        formulario = MedicamentoForm(instance=medicamento)

    return render(
        request,
        "formulario_medicamento.html",
        {
            "formulario": formulario,
            "modo": "editar",
            "medicamento": medicamento,
        },
    )


@permiso_requerido("medicamentos.eliminar")
@require_POST
def cambiar_estado_medicamento(request, medicamento_id):
    medicamento = get_object_or_404(Medicamento, pk=medicamento_id)
    medicamento.activo = not medicamento.activo
    medicamento.save(update_fields=["activo"])

    if medicamento.activo:
        messages.success(request, "Medicamento activado correctamente.")
    else:
        messages.success(request, "Medicamento desactivado correctamente.")

    return redirect("medicamentos")


@permiso_requerido("medicamentos.eliminar")
@require_POST
def eliminar_medicamento(request, medicamento_id):
    medicamento = get_object_or_404(Medicamento, pk=medicamento_id)
    nombre = medicamento.nombre_comercial

    try:
        medicamento.delete()
    except ProtectedError:
        messages.error(
            request,
            f"No se puede eliminar «{nombre}» porque está asociado "
            "a una o más recetas médicas. Puedes desactivarlo en su lugar.",
        )
    else:
        messages.success(
            request,
            f"El medicamento «{nombre}» se eliminó correctamente.",
        )

    return redirect("medicamentos")
