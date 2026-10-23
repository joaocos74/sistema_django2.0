from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .forms import ResolucaoForm
from .models import Resolucao


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
    return render(request, 'resolucoes/index.html', {
        'form': form, 'busca': busca, 'limite': settings.RESOLUCOES_MAX_BYTES,
        'pagina': Paginator(registros, 25).get_page(request.GET.get('page')),
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
