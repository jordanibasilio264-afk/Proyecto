from django.shortcuts import render
from apps.usuarios.decorators import requiere_permiso

@requiere_permiso("expedientes.ver")
def expedientes(request):
    return render(request,"expedientes.html")
