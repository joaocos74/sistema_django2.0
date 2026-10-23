import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .forms import ResolucaoForm, EditarResolucaoForm
from .models import Resolucao


def pode_editar(user, registro):
    return user.is_superuser or registro.adicionado_por_id == user.pk


def registro_para_editar(request, pk):
    registros = Resolucao.objects.all()
    if request.method == 'POST':
        registros = registros.select_for_update()
    registro = get_object_or_404(registros, pk=pk)
    if not pode_editar(request.user, registro):
        raise PermissionDenied('Somente o autor ou administrador pode alterar esta resolução.')
    return registro


@login_required
@require_http_methods(['GET', 'POST'])
def index(request):
    form = ResolucaoForm(request.POST if request.method == 'POST' else None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        registro = form.save(commit=False)
        registro.adicionado_por = request.user
        registro.nome_original = form.cleaned_data['arquivo'].name
        registro.tamanho = form.cleaned_data['arquivo'].size
        registro.save()
        messages.success(request, 'Resolução adicionada com sucesso!')
        return redirect('resolucoes:index')
    busca = request.GET.get('q', '').strip()
    registros = Resolucao.objects.select_related('adicionado_por')
    if busca:
        registros = registros.filter(Q(descricao__icontains=busca) | Q(nome_original__icontains=busca))
    pagina = Paginator(registros, 25).get_page(request.GET.get('page'))
    for registro in pagina:
        registro.pode_editar = pode_editar(request.user, registro)
    return render(request, 'resolucoes/index.html', {
        'form': form, 'busca': busca, 'limite': settings.RESOLUCOES_MAX_BYTES,
        'pagina': pagina,
    })


@login_required
@require_GET
def visualizar(request, pk):
    registro = get_object_or_404(Resolucao, pk=pk)
    try:
        arquivo = registro.arquivo.open('rb')
    except (FileNotFoundError, ValueError):
        raise Http404('PDF não encontrado.')
    response = FileResponse(arquivo, as_attachment=False, filename=registro.nome_original,
                            content_type='application/pdf')
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def editar(request, pk):
    registro = registro_para_editar(request, pk)
    form = EditarResolucaoForm(request.POST if request.method == 'POST' else None, instance=registro)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Resolução atualizada com sucesso!')
        return redirect('resolucoes:index')
    return render(request, 'resolucoes/editar.html', {'form': form, 'registro': registro})


def remover_pdf(arquivo):
    try:
        arquivo.delete(save=False)
    except OSError:
        logging.getLogger(__name__).exception('Não foi possível remover o PDF da resolução excluída.')


@login_required
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def excluir(request, pk):
    registro = registro_para_editar(request, pk)
    if request.method == 'POST':
        arquivo = registro.arquivo
        registro.delete()
        transaction.on_commit(lambda: remover_pdf(arquivo))
        messages.success(request, 'Resolução excluída com sucesso!')
        return redirect('resolucoes:index')
    return render(request, 'resolucoes/excluir.html', {'registro': registro})
