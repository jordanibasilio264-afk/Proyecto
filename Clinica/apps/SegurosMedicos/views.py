from django.shortcuts import render, redirect, get_object_or_404
from .models import Seguro


def gestion(request):
    seguros = Seguro.objects.all()

    buscar = request.GET.get("buscar")

    if buscar:
        seguros = Seguro.objects.filter(nombre__icontains=buscar)

    seguro_editar = None

    editar = request.GET.get("editar")

    if editar:
        seguro_editar = get_object_or_404(Seguro, id=editar)

    return render(request, "Seguros.html", {
        "seguros": seguros,
        "seguro_editar": seguro_editar
    })


def guardar(request):
    if request.method == "POST":

        id_seguro = request.POST.get("id")
        nombre = request.POST.get("nombre")
        numero = request.POST.get("numero")
        telefono = request.POST.get("telefono")
        estado = request.POST.get("estado")

        if id_seguro:
            seguro = get_object_or_404(Seguro, id=id_seguro)

            seguro.nombre = nombre
            seguro.numero = numero
            seguro.telefono = telefono
            seguro.estado = True if estado == "1" else False

            seguro.save()

        else:
            Seguro.objects.create(
                nombre=nombre,
                numero=numero,
                telefono=telefono,
                estado=True if estado == "1" else False
            )

        return redirect("seguros")


def eliminar(request, id):
    seguro = get_object_or_404(Seguro, id=id)
    seguro.delete()

    return redirect("seguros")