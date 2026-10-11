from django.shortcuts import render
from apps.usuarios.decorators import requiere_permiso

@requiere_permiso("citas.ver")
def citas(request):
    return render(request, "citas.html")