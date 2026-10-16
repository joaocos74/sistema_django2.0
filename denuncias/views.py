from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from register.consultas import buscar_por_documento, endereco_estabelecimento
from register.models import Estabelecimento
from .forms import DenunciaForm
from .models import Denuncia


def pode_editar(user, denuncia):
    return user.is_superuser or user.pk in (denuncia.criado_por_id, denuncia.fiscal_responsavel_id)


@login_required
@require_http_methods(['GET', 'POST'])
def denuncias_index(request):
    denuncia = None
    identificador = request.POST.get('denuncia_id') if request.method == 'POST' else request.GET.get('editar')
    if identificador:
        if not identificador.isascii() or not identificador.isdigit() or len(identificador) > 18:
            return JsonResponse({'erro': 'Denúncia inválida.'}, status=400)
        denuncia = get_object_or_404(Denuncia, pk=int(identificador))
        if request.method == 'POST' and not pode_editar(request.user, denuncia):
            raise PermissionDenied
    initial = {}
    if denuncia:
        initial['cadastro_id'] = denuncia.estabelecimento_id
    elif request.method == 'GET' and request.GET.get('estabelecimento', '').isdigit():
        identificador_est = request.GET['estabelecimento']
        if len(identificador_est) > 18:
            return JsonResponse({'erro': 'Estabelecimento inválido.'}, status=400)
        est = get_object_or_404(Estabelecimento, pk=int(identificador_est))
        initial = {'cadastro_id': est.pk, 'cnpj': est.cnpj, 'razao_social': est.razao_social,
                   'nome_fantasia': est.nome_fantasia, 'endereco': endereco_estabelecimento(est)}
    form = DenunciaForm(request.POST if request.method == 'POST' else None, instance=denuncia, initial=initial)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            if denuncia:
                atual = Denuncia.objects.select_for_update().get(pk=denuncia.pk)
                if not pode_editar(request.user, atual):
                    raise PermissionDenied
            registro = form.save(commit=False)
            registro.estabelecimento = form.estabelecimento
            if not denuncia:
                registro.criado_por = request.user
            registro.save()
        messages.success(request, 'Denúncia atualizada com sucesso!' if denuncia else 'Denúncia registrada com sucesso!')
        return redirect('denuncias:index')
    consulta = Denuncia.objects.select_related('fiscal_responsavel', 'estabelecimento')
    return render(request, 'denuncias/denuncias.html', {
        'form': form, 'denuncia': denuncia,
        'pode_editar': not denuncia or pode_editar(request.user, denuncia),
        'pagina': Paginator(consulta.order_by('-data_criacao', '-pk'), 25).get_page(request.GET.get('page')),
    })


@login_required
@require_GET
def buscar_cnpj(request):
    try:
        est = buscar_por_documento(request.GET.get('cnpj'))
    except ValidationError as error:
        return JsonResponse({'erro': ' '.join(error.messages)}, status=400)
    if not est:
        return JsonResponse({'existe': False})
    return JsonResponse({'existe': True, 'dados': {
        'id': est.pk, 'numero_pasta': est.numero_pasta, 'cnpj': est.cnpj, 'razao_social': est.razao_social,
        'nome_fantasia': est.nome_fantasia, 'endereco': endereco_estabelecimento(est),
    }})


def serializar(item):
    dados = {nome: getattr(item, nome) for nome in (
        'id', 'estabelecimento_id', 'cnpj', 'razao_social', 'nome_fantasia', 'endereco',
        'canal_entrada', 'tipo', 'motivo', 'data_denuncia', 'fiscal_responsavel_id',
        'data_tratativa', 'medidas_adotadas', 'status',
    )}
    dados['numero_pasta'] = item.estabelecimento.numero_pasta if item.estabelecimento_id else None
    return dados


@login_required
@require_GET
def listar_denuncias(request):
    pagina = Paginator(Denuncia.objects.select_related('estabelecimento').order_by('-data_criacao', '-pk'), 25).get_page(request.GET.get('page'))
    return JsonResponse({'resultados': [serializar(item) for item in pagina], 'paginas': pagina.paginator.num_pages})


@login_required
@require_GET
def get_denuncia(request, id):
    return JsonResponse(serializar(get_object_or_404(Denuncia, pk=id)))
