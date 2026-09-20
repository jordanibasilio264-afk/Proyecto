from django.shortcuts import render


def medicamentos_view(request):

    return render(
        request,
        'medicamentos.html'
    )