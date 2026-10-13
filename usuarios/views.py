from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from .forms import CadastroUsuarioForm, LoginForm, PerfilForm


class EntrarView(LoginView):
    template_name = 'usuarios/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class AlterarSenhaView(PasswordChangeView):
    template_name = 'usuarios/formulario.html'
    success_url = reverse_lazy('usuarios:perfil')
    extra_context = {'titulo': 'Alterar senha', 'botao': 'Salvar nova senha'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Senha alterada com sucesso.')
        return response


@login_required
@require_http_methods(['GET', 'POST'])
def perfil_view(request):
    form = PerfilForm(request.POST if request.method == 'POST' else None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Perfil atualizado com sucesso.')
        return redirect('usuarios:perfil')
    return render(request, 'usuarios/formulario.html', {
        'form': form, 'titulo': 'Meu perfil', 'botao': 'Salvar perfil', 'perfil': True,
    })


@login_required
def listar_view(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    busca = request.GET.get('q', '').strip()[:150]
    usuarios = get_user_model().objects.order_by('username', 'pk')
    if busca:
        usuarios = usuarios.filter(
            Q(username__icontains=busca) | Q(first_name__icontains=busca)
            | Q(last_name__icontains=busca) | Q(email__icontains=busca)
        )
    return render(request, 'usuarios/listar.html', {
        'pagina': Paginator(usuarios, 25).get_page(request.GET.get('page')),
        'busca': busca,
    })


@require_http_methods(['GET', 'POST'])
def cadastrar_view(request):
    if request.user.is_authenticated:
        return redirect('home:index')
    form = CadastroUsuarioForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Usuário cadastrado com sucesso. Agora você já pode entrar.')
        return redirect('usuarios:login')
    return render(request, 'usuarios/cadastrar.html', {'form': form})
