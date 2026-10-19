from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import EspecialidadForm
from .models import Especialidad
class PermisoMixin(LoginRequiredMixin, UserPassesTestMixin):
    permiso = None

    def test_func(self):
        return self.request.user.tiene_permiso(self.permiso)


class EspecialidadListView(PermisoMixin, ListView):
    permiso = "especialidades.ver"
    model = Especialidad
    template_name = "usuarios/especialidad_lista.html"
    paginate_by = 20

    def get_queryset(self):
        return Especialidad.objects.annotate(total_medicos=Count("medicos"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        ctx["puede_crear"] = u.tiene_permiso("especialidades.crear")
        ctx["puede_editar"] = u.tiene_permiso("especialidades.editar")
        ctx["puede_eliminar"] = u.tiene_permiso("especialidades.eliminar")
        return ctx


class EspecialidadCreateView(PermisoMixin, CreateView):
    permiso = "especialidades.crear"
    model = Especialidad
    form_class = EspecialidadForm
    template_name = "usuarios/especialidad_form.html"
    success_url = reverse_lazy("usuarios:especialidad_lista")

    def form_valid(self, form):
        messages.success(self.request, "Especialidad registrada.")
        return super().form_valid(form)


class EspecialidadUpdateView(PermisoMixin, UpdateView):
    permiso = "especialidades.editar"
    model = Especialidad
    form_class = EspecialidadForm
    template_name = "usuarios/especialidad_form.html"
    success_url = reverse_lazy("usuarios:especialidad_lista")

    def form_valid(self, form):
        messages.success(self.request, "Especialidad actualizada.")
        return super().form_valid(form)


class EspecialidadDeleteView(PermisoMixin, DeleteView):
    permiso = "especialidades.eliminar"
    model = Especialidad
    template_name = "usuarios/especialidad_eliminar.html"
    success_url = reverse_lazy("usuarios:especialidad_lista")

    def post(self, request, *args, **kwargs):
        esp = self.get_object()
        if esp.medicos.exists():
            messages.error(
                request,
                f"No se puede eliminar «{esp}»: está asociada a "
                f"{esp.medicos.count()} médico(s). Desactívala o quítala de los médicos.",
            )
            return redirect(self.success_url)
        messages.success(request, "Especialidad eliminada.")
        return super().post(request, *args, **kwargs)