from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .forms import ArquivoForm
from .models import Arquivo


@login_required
@require_http_methods(['GET', 'POST'])
def index(request):
    form = ArquivoForm(request.POST if request.method == 'POST' else None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        registro = form.save(commit=False)
        registro.enviado_por = request.user
        registro.nome_original = form.cleaned_data['arquivo'].name
        registro.tamanho = form.cleaned_data['arquivo'].size
        registro.save()
        messages.success(request, 'Arquivo adicionado com sucesso!')
        return redirect('arquivos:index')
    busca = request.GET.get('q', '').strip()
    registros = Arquivo.objects.select_related('enviado_por')
    if busca:
        registros = registros.filter(Q(nome__icontains=busca) | Q(descricao__icontains=busca)
                                     | Q(nome_original__icontains=busca))
    return render(request, 'arquivos/index.html', {
        'form': form, 'busca': busca, 'limite': settings.ARQUIVOS_MAX_BYTES,
        'pagina': Paginator(registros, 25).get_page(request.GET.get('page')),
    })


@login_required
@require_GET
def baixar(request, pk):
    registro = get_object_or_404(Arquivo, pk=pk)
    try:
        arquivo = registro.arquivo.open('rb')
    except (FileNotFoundError, ValueError):
        raise Http404('Arquivo não encontrado.')
    response = FileResponse(arquivo, as_attachment=True, filename=registro.nome_original,
                            content_type='application/octet-stream')
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response
