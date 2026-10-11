from django.shortcuts import render

from apps.usuarios.decorators import requiere_permiso

@requiere_permiso("medicamentos.ver")
def medicamentos_view(request):

    return render(
        request,
        'medicamentos.html'
    )