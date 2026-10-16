from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from register.consultas import buscar_por_documento
from .forms import LiberacaoForm
from .models import RegistroRedesim


def dados_estabelecimento(estabelecimento):
    tipo = estabelecimento.tipos.order_by('-pk').first()
    vigilancia = estabelecimento.fiscalizacoes.select_related('fiscal').order_by('-pk').first()
    fiscal = vigilancia.fiscal if vigilancia else None
    return {
        'id': estabelecimento.pk,
        'numero_pasta': estabelecimento.numero_pasta,
        'razao_social': estabelecimento.razao_social,
        'nome_fantasia': estabelecimento.nome_fantasia,
        'cnpj_ou_cpf': estabelecimento.cnpj,
        'nivel': {'I': 'NIVEL 1', 'II': 'NIVEL 2', 'III': 'NIVEL 3', 'IV': 'NIVEL 4'}.get(tipo.risco, '') if tipo else '',
        'classe': tipo.classe if tipo else '',
        'cnae_principal': tipo.cnae_principal if tipo else '',
        'fiscal_responsavel': (fiscal.get_full_name() or fiscal.username) if fiscal else '',
        'alvara': vigilancia.data_alvara.isoformat() if vigilancia and vigilancia.data_alvara else '',
        'observacoes': vigilancia.obs if vigilancia else '',
    }, vigilancia


@login_required
@require_http_methods(['GET', 'POST'])
def redesim_index(request):
    if request.method == 'GET':
        return render(request, 'redesim/redesim.html', {'hoje': timezone.localdate()})
    form = LiberacaoForm(request.POST)
    if not form.is_valid():
        for erros in form.errors.values():
            for erro in erros:
                messages.error(request, erro)
        return redirect('redesim:index')
    valores = form.cleaned_data
    try:
        with transaction.atomic():
            estabelecimento = buscar_por_documento(valores['cnpj_ou_cpf'], bloquear=True)
            if not estabelecimento or estabelecimento.pk != valores['estabelecimento_id']:
                raise ValidationError('O cadastro não corresponde ao documento. Faça uma nova busca.')
            dados, vigilancia = dados_estabelecimento(estabelecimento)
            if vigilancia is None:
                raise ValidationError('O estabelecimento não possui registro de fiscalização. Regularize o cadastro em Analisar antes de registrar a liberação.')
            vigilancia.data_alvara = valores['alvara']
            vigilancia.obs = valores['observacoes']
            vigilancia.full_clean()
            vigilancia.save(update_fields=['data_alvara', 'obs'])
            registro = RegistroRedesim(
                estabelecimento=estabelecimento, fiscal=request.user,
                razao_social=dados['razao_social'], nome_fantasia=dados['nome_fantasia'],
                cnpj_cpf=dados['cnpj_ou_cpf'], nivel=dados['nivel'], classe=dados['classe'],
                cnae_principal=dados['cnae_principal'],
                fiscal_responsavel=dados['fiscal_responsavel'],
                fiscal_matricula=vigilancia.fiscal.username,
                data_liberacao=valores['alvara'], observacoes=valores['observacoes'],
            )
            registro.full_clean()
            registro.save()
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
        return redirect('redesim:index')
    messages.success(request, 'Registro REDESIM salvo com sucesso!')
    return redirect('redesim:index')


@login_required
@require_GET
def buscar_cnpj(request):
    try:
        estabelecimento = buscar_por_documento(request.GET.get('documento') or request.GET.get('cnpj') or request.GET.get('cpf'))
    except ValidationError as error:
        return JsonResponse({'existe': False, 'mensagem': ' '.join(error.messages)}, status=400)
    if not estabelecimento:
        return JsonResponse({'existe': False, 'mensagem': 'Estabelecimento não encontrado. Cadastre-o antes de registrar uma liberação.'})
    dados, vigilancia = dados_estabelecimento(estabelecimento)
    return JsonResponse({'existe': True, 'dados': dados})


@login_required
@require_GET
def listar_redesim(request):
    return JsonResponse([
        {'cadastro_id': item.estabelecimento_id, 'numero_pasta': item.estabelecimento.numero_pasta, 'nivel': item.nivel, 'classe': item.classe,
         'razao_social': item.razao_social, 'cnpj_ou_cpf': item.cnpj_cpf,
         'alvara': item.data_liberacao.strftime('%d/%m/%Y') if item.data_liberacao else '',
         'fiscal_liberacao': (item.fiscal.get_full_name() or item.fiscal.username) if item.fiscal else 'Usuário removido'}
        for item in RegistroRedesim.objects.select_related('fiscal', 'estabelecimento').order_by('-criado_em', '-pk')
    ], safe=False)
