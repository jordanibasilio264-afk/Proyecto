from django.shortcuts import render
def login_view(request):
    return render(request, 'login.html')
def gestor_view(request):
    return render(request, 'gestor_usuarios.html')
# Create your views here.
