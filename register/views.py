import json
from datetime import datetime, date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q, Subquery
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404

from .models import Estabelecimento, Tipo, Responsavel, RTResponsavel, Vigilancia, Documento
from .forms import EstabelecimentoForm, AnaliseEstabelecimentoForm, InspecaoForm, NumeroPastaForm
from .inspecoes import com_inspecao_atual


def texto_titulo(valor):
    #Normaliza texto para iniciais maiúsculas, preservando conectivos comuns.
    valor = (valor or '').strip()
    if not valor:
        return ''

    conectivos = {'da', 'de', 'do', 'das', 'dos', 'e'}
    palavras = []
    for palavra in valor.lower().split():
        if palavra in conectivos:
            palavras.append(palavra)
        else:
            palavras.append(palavra[:1].upper() + palavra[1:])
    return ' '.join(palavras)


def texto_maiusculo(valor):
    return (valor or '').strip().upper()


def texto_livre(valor):
    return (valor or '').strip()


def formatar_telefone(valor):
    digitos = ''.join(ch for ch in (valor or '') if ch.isdigit())

    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    if len(digitos) == 10:
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"

    return (valor or '').strip()

def converter_para_data(data_str):
    #Converte datas recebidas em string (YYYY-MM-DD ou DD/MM/YYYY) para objetos date reais do Python.
    if not data_str:
        return None
    if isinstance(data_str, (date, datetime)):
        return data_str if isinstance(data_str, date) else data_str.date()
    
    data_str = str(data_str).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            return datetime.strptime(data_str, fmt).date()
        except ValueError:
            pass
    return None


@login_required
def cadastrar_estabelecimento_view(request):
    # Se o usuário for superusuário, ele pode escolher o fiscal responsável; caso contrário, o fiscal é o próprio usuário logado.
    fiscais = User.objects.all().order_by('first_name', 'username') if request.user.is_superuser else None
    
    form = EstabelecimentoForm(
        request.POST if request.method == 'POST' else None, user=request.user,
    )
    contexto = {'form': form, 'fiscais': fiscais, 'ano_atual': date.today().year}

    if request.method == 'POST':
        if not form.is_valid():
            return render(request, 'register/cadastrar.html', contexto)
        post = form.dados_para_cadastro()
        data_realizacao_obj = converter_para_data(post.get('data_realizacao'))
        if data_realizacao_obj and data_realizacao_obj > date.today():
            messages.error(request, "Não é permitido cadastrar uma inspeção com data de realização futura.")

       
            return render(request, 'register/cadastrar.html', contexto)


        try: 
            with transaction.atomic(): # regra do tudo ou nada: se qualquer parte falhar, não deve haver nenhum registro parcial.


                # 1. Fiscal responsável
                if request.user.is_superuser:
                    fiscal_id = post.get('fiscal_responsavel')
                    fiscal_obj = User.objects.filter(id=fiscal_id).first() or request.user
                else:
                    fiscal_obj = request.user

                # 2. O estabelecimento vem primeiro: as outras tabelas apontam para ele.
                estabelecimento = Estabelecimento(
                    cnpj=texto_livre(post.get('cnpj', post.get('cnpj_cpf'))),
                    nome_fantasia=texto_titulo(post.get('nome_fantasia')),
                    razao_social=texto_titulo(post.get('razao_social')),
                    n_parecer=texto_maiusculo(post.get('n_parecer', post.get('numero_parecer_tecnico', ''))),
                    logradouro=texto_titulo(post.get('estab_logradouro')),
                    numero=texto_livre(post.get('estab_numero', '')),
                    bairro=texto_titulo(post.get('estab_bairro')),
                    cidade=texto_titulo(post.get('estab_cidade', 'Taiobeiras')),
                    uf=texto_maiusculo(post.get('estab_uf', 'MG')),
                    cep=texto_livre(post.get('estab_cep', '')),
                    phone=formatar_telefone(post.get('estab_phone', post.get('estab_telefone', ''))),
                    email=texto_livre(post.get('estab_email', '')).lower(),
                    insc_municipal=texto_livre(post.get('insc_municipal', '')),
                    latitude=post.get('latitude') or None,
                    longitude=post.get('longitude') or None,
                    status=False,  # Desmarcado significa ativo.
                )
                estabelecimento.save(usuario=request.user)

                # 3. Classificação vinculada ao estabelecimento
                Tipo.objects.create(
                    estabelecimento=estabelecimento,
                    alterado_por=fiscal_obj,
                    risco=texto_maiusculo(post.get('risco', 'I')),
                    cnae_principal=texto_livre(post.get('cnae_principal', '')),
                    cnae_secundaria=texto_livre(post.get('cnae_secundaria', '')),
                    classe=texto_maiusculo(post.get('classe', '')),
                )

                # 4. Responsável pelo estabelecimento
                resp_nome = post.get('resp_nome', '').strip() # Validar o cadastro apenas se o usuário tiver preenchido o nome do RT no formulário.
                if resp_nome:
                    Responsavel.objects.create(
                        estabelecimento=estabelecimento,
                        nome=texto_titulo(resp_nome),
                        nacionalidade=texto_titulo(post.get('resp_nacionalidade', '')),
                        naturalidade=texto_titulo(post.get('resp_naturalidade', '')),
                        estado_civil=texto_livre(post.get('resp_estado_civil', '')),
                        profissao=texto_titulo(post.get('resp_profissao', '')),
                        cpf=texto_livre(post.get('resp_cpf', '')),
                        rg=texto_livre(post.get('resp_rg', '')),
                        phone=formatar_telefone(post.get('resp_phone', post.get('resp_telefone', ''))),
                        logradouro=texto_titulo(post.get('resp_logradouro')),
                        numero=texto_livre(post.get('resp_numero', '')),
                        bairro=texto_titulo(post.get('resp_bairro')),
                        cidade=texto_titulo(post.get('resp_cidade', 'Taiobeiras')),
                        uf=texto_maiusculo(post.get('resp_uf', 'MG')),
                    )

                # 5. Responsável técnico
                rt_nome = post.get('rt_nome', '').strip() # Validar o cadastro apenas se o usuário tiver preenchido o nome do RT no formulário.
                if any(post.get(f'rt_{campo}') for campo in form.campos_rt):
                    RTResponsavel.objects.create(
                        estabelecimento=estabelecimento,
                        nome=texto_titulo(rt_nome),
                        nacionalidade=texto_titulo(post.get('rt_nacionalidade', '')),
                        naturalidade=texto_titulo(post.get('rt_naturalidade', '')),
                        estado_civil=texto_livre(post.get('rt_estado_civil', '')),
                        profissao=texto_titulo(post.get('rt_profissao', '')),
                        cpf=texto_livre(post.get('rt_cpf', '')),
                        rg=texto_livre(post.get('rt_rg', '')),
                        rg_conselho=texto_maiusculo(post.get('rt_rg_conselho', post.get('rt_conselho', ''))),
                        phone=formatar_telefone(post.get('rt_phone', post.get('rt_telefone', ''))),
                        logradouro=texto_titulo(post.get('rt_logradouro')),
                        numero=texto_livre(post.get('rt_numero', '')),
                        bairro=texto_titulo(post.get('rt_bairro')),
                        cidade=texto_titulo(post.get('rt_cidade', 'Taiobeiras')),
                        uf=texto_maiusculo(post.get('rt_uf', 'MG')),
                    )

                # 6. Registro de vigilância inicial
                data_alvara_obj = converter_para_data(post.get('data_alvara'))
                ano_atual = date.today().year
                mes_previsto_val = int(post.get('mes_previsto')) if post.get('mes_previsto') else None

                if data_realizacao_obj:
                    ano_previsto_val = int(post.get('ano_previsto') or data_realizacao_obj.year)
                    mes_previsto_val = mes_previsto_val or data_realizacao_obj.month
                    status_inicial = Vigilancia.Status.CONCLUIDO
                else:
                    ano_previsto_val = int(post.get('ano_previsto') or ano_atual)
                    status_inicial = post.get('inspecao_status', Vigilancia.Status.A_FAZER)

                Vigilancia.objects.create(
                    estabelecimento=estabelecimento,
                    fiscal=fiscal_obj,
                    inspecao_status=status_inicial,
                    plano_aplicado=post.get('plano_aplicado', Vigilancia.Relatado.NAO_REQUERIDO),
                    plano_status=post.get('plano_status') or None,
                    termo_ciencia=post.get('termo_ciencia', Vigilancia.Relatado.NAO_REQUERIDO),
                    termo_status=post.get('termo_status') or None,
                    interdicao=post.get('interdicao', Vigilancia.Relatado.NAO_REQUERIDO),
                    interdicao_status=post.get('interdicao_status') or None,
                    processo=post.get('processo', Vigilancia.Relatado.NAO_REQUERIDO),
                    processo_status=post.get('processo_status') or None,
                    ano_previsto=ano_previsto_val,
                    mes_previsto=mes_previsto_val,
                    data_realizacao=data_realizacao_obj,
                    data_alvara=data_alvara_obj,
                    obs=texto_livre(post.get('obs', post.get('observacoes', ''))),
                )

                messages.success(request, f"Estabelecimento '{estabelecimento.razao_social}' cadastrado com sucesso!")
                return redirect('register_view:register_view')

        except Exception:
            messages.error(request, "Não foi possível salvar o cadastro. Confira os dados e tente novamente.")

    fiscais = User.objects.all().order_by('first_name', 'username') if request.user.is_superuser else None
    return render(request, 'register/cadastrar.html', contexto)


# Como classificação e fiscal agora ficam nas tabelas relacionadas,
# usamos o último registro para identificar a situação atual do estabelecimento.
def _estabelecimentos_visiveis(user):
    ultima_vigilancia = Vigilancia.objects.filter(estabelecimento_id=OuterRef('pk')).order_by('-id')
    ultimo_tipo = Tipo.objects.filter(estabelecimento_id=OuterRef('pk')).order_by('-id')
    estabelecimentos = Estabelecimento.objects.annotate(
        fiscal_atual_id=Subquery(ultima_vigilancia.values('fiscal_id')[:1]),
        tipo_risco=Subquery(ultimo_tipo.values('risco')[:1]),
        tipo_classe=Subquery(ultimo_tipo.values('classe')[:1]),
    )
    # Todos os usuários logados podem consultar todos os estabelecimentos.
    # A permissão de alteração é verificada nas operações de escrita.
    return estabelecimentos


def _fiscais_visiveis(user):
    fiscais = User.objects.all()
    return fiscais.order_by('first_name', 'username')


@login_required
def pesquisar_estabelecimentos_view(request):
    ano_inspecao = timezone.localdate().year
    try:
        if request.GET.get('inspecao_mes'):
            ano_inspecao = datetime.strptime(request.GET['inspecao_mes'], '%Y-%m').year
    except ValueError:
        pass  # A validação do período abaixo informa o erro ao usuário.
    estabelecimentos = com_inspecao_atual(
        _estabelecimentos_visiveis(request.user), ano_inspecao,
    ).order_by('numero_pasta', 'pk')
    filtros = {
        'cnpj': 'cnpj__icontains',
        'nome_fantasia': 'nome_fantasia__icontains',
        'razao_social': 'razao_social__icontains',
        'bairro': 'bairro__icontains',
        'risco': 'tipo_risco',
        'classe': 'tipo_classe__icontains',
    }
    for parametro, campo in filtros.items():
        valor = request.GET.get(parametro, '').strip()
        if parametro == 'cnpj':
            valor = valor or request.GET.get('cnpj_cpf', '').strip()
        if valor:
            estabelecimentos = estabelecimentos.filter(**{campo: valor})

    for parametro, campo in (('id', 'numero_pasta'), ('fiscal_responsavel', 'fiscal_atual_id')):
        valor = request.GET.get(parametro, '').strip()
        if valor and valor != 'todos':
            if valor.isascii() and valor.isdigit() and len(valor) <= 18:
                estabelecimentos = estabelecimentos.filter(**{campo: int(valor)})
            else:
                estabelecimentos = estabelecimentos.none()

    endereco = request.GET.get('endereco', '').strip()
    if endereco:
        estabelecimentos = estabelecimentos.filter(
            Q(logradouro__icontains=endereco) | Q(numero__icontains=endereco)
        )
    status = request.GET.get('inspecao_status', request.GET.get('status', '')).strip()
    if status:
        estabelecimentos = estabelecimentos.filter(inspecao_status_atual=status)

    for parametro in ('inspecao_mes', 'alvara_mes'):
        valor = request.GET.get(parametro, '').strip()
        if not valor:
            continue
        try:
            periodo = datetime.strptime(valor, '%Y-%m')
        except ValueError:
            messages.error(request, 'Informe o período no formato AAAA-MM.')
            estabelecimentos = estabelecimentos.none()
            continue
        if parametro == 'inspecao_mes':
            estabelecimentos = estabelecimentos.filter(
                Q(inspecao_realizada_em__year=periodo.year,
                  inspecao_realizada_em__month=periodo.month)
                | Q(inspecao_ano_previsto=periodo.year,
                    inspecao_mes_previsto=periodo.month)
            )
        else:
            estabelecimentos = estabelecimentos.filter(
                inspecao_alvara_em__year=periodo.year,
                inspecao_alvara_em__month=periodo.month,
            )

    ativo = request.GET.get('ativo', '1').strip()
    if ativo in ('1', '0'):
        estabelecimentos = estabelecimentos.filter(status=(ativo == '0'))

    estabelecimentos = list(estabelecimentos.distinct())
    ultimas = {}
    for vigilancia in Vigilancia.objects.filter(
        estabelecimento__in=estabelecimentos
    ).select_related('fiscal').order_by('estabelecimento_id', '-id'):
        ultimas.setdefault(vigilancia.estabelecimento_id, vigilancia)
    for estabelecimento in estabelecimentos:
        estabelecimento.ultima_vigilancia = ultimas.get(estabelecimento.pk)

    return render(request, 'register/pesquisar.html', {
        'estabelecimentos': estabelecimentos,
        'ativo_selecionado': ativo,
        'ano_inspecao': ano_inspecao,
        'riscos': Tipo.Risco.choices,
        'fiscais': _fiscais_visiveis(request.user),
    })


def _contexto_analise(request, estabelecimento, pode_editar, form=None, inspecao_form=None):
    vigilancia = estabelecimento.fiscalizacoes.select_related('fiscal').order_by('-id').first()
    tipo = estabelecimento.tipos.order_by('-id').first()
    responsavel = estabelecimento.responsavel.order_by('-id').first()
    tecnico = estabelecimento.responsavel_tecnico.order_by('-id').first()
    if form is None:
        initial = {'ativo': '0' if estabelecimento.status else '1',
                   'fiscal_responsavel': vigilancia.fiscal_id if vigilancia else request.user.pk}
        for objeto, campos, prefixo in (
            (tipo, EstabelecimentoForm.campos_tipo, ''),
            (responsavel, EstabelecimentoForm.campos_responsavel, 'resp_'),
            (tecnico, EstabelecimentoForm.campos_rt, 'rt_'),
        ):
            if objeto:
                initial.update({f'{prefixo}{campo}': getattr(objeto, campo) for campo in campos})
        form = AnaliseEstabelecimentoForm(instance=estabelecimento, initial=initial, user=request.user)
        if not pode_editar:
            form.fields['fiscal_responsavel'].queryset = User.objects.all()
        elif request.user.is_superuser and vigilancia:
            form.fields['fiscal_responsavel'].queryset = User.objects.filter(Q(is_active=True) | Q(pk=vigilancia.fiscal_id))
    if inspecao_form is None:
        inspecao_form = InspecaoForm(instance=vigilancia)
    return {
        'estabelecimento': estabelecimento, 'licenca': estabelecimento,
        'numero_pasta_form': NumeroPastaForm(initial={'numero_pasta': estabelecimento.numero_pasta}),
        'historico_pastas': estabelecimento.historico_pastas.select_related('alterado_por').all(),
        'form': form, 'inspecao_form': inspecao_form, 'tipo': tipo,
        'responsavel': responsavel, 'responsavel_tecnico': tecnico,
        'vigilancia': vigilancia, 'pode_editar': pode_editar,
        'historico_tipos': estabelecimento.tipos.select_related('alterado_por').order_by('created_at', 'id'),
        'historico_vigilancias': estabelecimento.fiscalizacoes.select_related('fiscal').order_by('created_at', 'id'),
        'documentos': estabelecimento.documentos.select_related('enviado_por').order_by('-id'),
        'historico_denuncias': estabelecimento.denuncias.select_related('fiscal_responsavel').order_by('-data_criacao', '-pk'),
        'tipos_documento': Documento.TipoDocumento.choices,
        'fiscais': _fiscais_visiveis(request.user),
    }


@login_required
@require_POST
def alterar_numero_pasta(request, pk):
    if not request.user.is_superuser:
        raise PermissionDenied
    form = NumeroPastaForm(request.POST)
    if form.is_valid():
        try:
            with transaction.atomic():
                est = get_object_or_404(Estabelecimento.objects.select_for_update(), pk=pk)
                est.numero_pasta = form.cleaned_data['numero_pasta']
                est.save(update_fields=['numero_pasta', 'updated_at'], usuario=request.user)
            messages.success(request, f'Número da pasta atualizado para {est.numero_pasta}. Os vínculos foram preservados.')
        except ValidationError as erro:
            messages.error(request, ' '.join(erro.messages))
    else:
        messages.error(request, 'Informe um número de pasta inteiro e positivo válido.')
    return redirect('register_view:analisar', pk=pk)


@login_required
def analisar_estabelecimento_view(request, pk):
    estabelecimento = get_object_or_404(_estabelecimentos_visiveis(request.user), pk=pk)
    vigilancia_exibir = estabelecimento.fiscalizacoes.select_related('fiscal').order_by('-id').first()
    pode_editar = request.user.is_superuser or (
        vigilancia_exibir is not None and vigilancia_exibir.fiscal_id == request.user.pk
    )

    form = None
    inspecao_form = None
    if request.method == 'POST':
        if not pode_editar:
            messages.error(request, 'Você não tem permissão para alterar este estabelecimento.')
            return redirect(request.path)

        if 'excluir_doc_id' not in request.POST and 'btn_upload_doc' not in request.POST:
            form = AnaliseEstabelecimentoForm(request.POST, instance=estabelecimento, user=request.user)
            if request.user.is_superuser and vigilancia_exibir:
                form.fields['fiscal_responsavel'].queryset = User.objects.filter(Q(is_active=True) | Q(pk=vigilancia_exibir.fiscal_id))
            inspecao_form = InspecaoForm(request.POST, instance=vigilancia_exibir)
            cadastro_valido = form.is_valid()
            inspecao_valida = inspecao_form.is_valid()
            if not cadastro_valido or not inspecao_valida:
                return render(request, 'register/analisar.html', _contexto_analise(
                    request, estabelecimento, pode_editar, form, inspecao_form,
                ))

        try:
            with transaction.atomic():
                estabelecimento = get_object_or_404(
                    _estabelecimentos_visiveis(request.user).select_for_update(), pk=pk
                )
                if not request.user.is_superuser and estabelecimento.fiscal_atual_id != request.user.pk:
                    messages.error(request, 'Você não tem permissão para alterar este estabelecimento.')
                    return redirect(request.path)
                if 'excluir_doc_id' in request.POST:
                    doc_id = request.POST.get('excluir_doc_id', '')
                    if not doc_id.isascii() or not doc_id.isdigit() or len(doc_id) > 18:
                        raise ValidationError('Documento inválido.')
                    documento = get_object_or_404(Documento, pk=int(doc_id), estabelecimento=estabelecimento)
                    arquivo = documento.arquivo
                    documento.delete()
                    # Exclui o arquivo somente depois de confirmar a exclusão no banco.
                    transaction.on_commit(lambda: arquivo.delete(save=False))
                    messages.success(request, 'Documento removido com sucesso!')
                    return redirect(request.path)

                if 'btn_upload_doc' in request.POST:
                    arquivo = request.FILES.get('doc_arquivo')
                    nome = texto_livre(request.POST.get('doc_nome', request.POST.get('doc_titulo', '')))
                    if not nome or not arquivo:
                        raise ValidationError('Preencha o nome e selecione um documento.')
                    documento = Documento(
                        estabelecimento=estabelecimento,
                        tipo_documento=request.POST.get('tipo_documento', Documento.TipoDocumento.OUTRO),
                        nome=nome,
                        arquivo=arquivo,
                        enviado_por=request.user,
                    )
                    documento.full_clean()
                    documento.save()
                    messages.success(request, 'Documento anexado com sucesso!')
                    return redirect(request.path)

                data_realizacao = converter_para_data(request.POST.get('data_realizacao'))
                data_alvara = converter_para_data(request.POST.get('data_alvara'))
                for campo, valor in (('data_realizacao', data_realizacao), ('data_alvara', data_alvara)):
                    if request.POST.get(campo) and valor is None:
                        raise ValidationError('Informe uma data válida.')
                if data_realizacao and data_realizacao > date.today():
                    raise ValidationError('Não é permitido salvar uma inspeção com data futura.')

                ultima = estabelecimento.fiscalizacoes.order_by('-id').first()
                fiscal = ultima.fiscal if ultima else request.user
                if request.user.is_superuser:
                    fiscal_id = request.POST.get('fiscal_responsavel', '').strip()
                    if fiscal_id:
                        if not fiscal_id.isascii() or not fiscal_id.isdigit() or len(fiscal_id) > 18:
                            raise ValidationError('Fiscal inválido.')
                        fiscal = User.objects.filter(pk=int(fiscal_id)).filter(Q(is_active=True) | Q(pk=fiscal.pk)).first()
                        if fiscal is None:
                            raise ValidationError('Selecione um fiscal ativo.')

                estabelecimento.cnpj = texto_livre(request.POST.get('cnpj', request.POST.get('cnpj_cpf', estabelecimento.cnpj)))
                estabelecimento.nome_fantasia = texto_titulo(request.POST.get('nome_fantasia', estabelecimento.nome_fantasia))
                estabelecimento.razao_social = texto_titulo(request.POST.get('razao_social', estabelecimento.razao_social))
                estabelecimento.n_parecer = texto_maiusculo(request.POST.get('n_parecer', request.POST.get('numero_parecer_tecnico', estabelecimento.n_parecer)))
                for campo in ('logradouro', 'bairro', 'cidade'):
                    if f'estab_{campo}' in request.POST:
                        setattr(estabelecimento, campo, texto_titulo(request.POST.get(f'estab_{campo}')))
                for campo in ('numero', 'cep'):
                    if f'estab_{campo}' in request.POST:
                        setattr(estabelecimento, campo, texto_livre(request.POST.get(f'estab_{campo}')))
                if 'estab_uf' in request.POST:
                    estabelecimento.uf = texto_maiusculo(request.POST.get('estab_uf'))
                if 'estab_phone' in request.POST or 'estab_telefone' in request.POST:
                    estabelecimento.phone = formatar_telefone(request.POST.get('estab_phone', request.POST.get('estab_telefone')))
                if 'estab_email' in request.POST:
                    estabelecimento.email = texto_livre(request.POST.get('estab_email')).lower()
                if 'insc_municipal' in request.POST:
                    estabelecimento.insc_municipal = texto_livre(request.POST.get('insc_municipal'))
                for campo in ('latitude', 'longitude'):
                    if campo in request.POST:
                        setattr(estabelecimento, campo, request.POST.get(campo) or None)
                if 'ativo' in request.POST:
                    estabelecimento.status = request.POST.get('ativo') != '1'
                elif 'status' in request.POST:
                    estabelecimento.status = request.POST.get('status') in ('1', 'true', 'on')
                estabelecimento.full_clean()
                estabelecimento.save(usuario=request.user)

                # Uma mudança de classificação gera outro registro, preservando o histórico.
                tipo = estabelecimento.tipos.order_by('-id').first()
                campos_tipo = ('risco', 'cnae_principal', 'cnae_secundaria', 'classe')
                if any(campo in request.POST for campo in campos_tipo):
                    dados_tipo = {
                        campo: texto_livre(request.POST.get(campo, getattr(tipo, campo, '')))
                        for campo in campos_tipo
                    }
                    dados_tipo['risco'] = dados_tipo['risco'].upper()
                    dados_tipo['classe'] = dados_tipo['classe'].upper()
                    if tipo is None or any(getattr(tipo, campo) != valor for campo, valor in dados_tipo.items()):
                        novo_tipo = Tipo(estabelecimento=estabelecimento, alterado_por=fiscal, **dados_tipo)
                        novo_tipo.full_clean()
                        novo_tipo.save()

                for modelo, prefixo in ((Responsavel, 'resp'), (RTResponsavel, 'rt')):
                    campos = (
                        'nome', 'nacionalidade', 'naturalidade', 'estado_civil', 'rg',
                        'profissao', 'cpf', 'logradouro', 'numero', 'bairro', 'cidade', 'uf', 'phone',
                    )
                    if modelo == RTResponsavel:
                        campos += ('rg_conselho',)
                    # Se a seção não foi enviada, mantém os dados existentes.
                    if not any(chave.startswith(f'{prefixo}_') for chave in request.POST):
                        continue
                    responsavel = modelo.objects.filter(estabelecimento=estabelecimento).order_by('-id').first()
                    dados = {}
                    for campo in campos:
                        chave = f'{prefixo}_{campo}'
                        alternativa = {'phone': f'{prefixo}_telefone', 'rg_conselho': 'rt_conselho'}.get(campo, chave)
                        valor = request.POST.get(chave, request.POST.get(alternativa, getattr(responsavel, campo, '') or ''))
                        if campo in ('nome', 'nacionalidade', 'naturalidade', 'profissao', 'logradouro', 'bairro', 'cidade'):
                            valor = texto_titulo(valor)
                        elif campo in ('uf', 'rg_conselho'):
                            valor = texto_maiusculo(valor)
                        elif campo == 'phone':
                            valor = formatar_telefone(valor)
                        else:
                            valor = texto_livre(valor)
                        dados[campo] = valor
                    if not any(dados.values()):
                        continue
                    if responsavel is None:
                        responsavel = modelo(estabelecimento=estabelecimento)
                    for campo, valor in dados.items():
                        setattr(responsavel, campo, valor)
                    responsavel.full_clean()
                    responsavel.save()

                # Conclui um agendamento ou registra uma nova inspeção, como no original.
                ano_ref = int(request.POST.get('ano_previsto') or (data_realizacao.year if data_realizacao else date.today().year))
                pendente = estabelecimento.fiscalizacoes.filter(
                    ano_previsto=ano_ref, data_realizacao__isnull=True,
                ).order_by('id').first()
                if data_realizacao:
                    if pendente:
                        vigilancia = pendente
                    elif ultima and ultima.data_realizacao == data_realizacao:
                        vigilancia = ultima
                    else:
                        vigilancia = Vigilancia(estabelecimento=estabelecimento, ano_previsto=ano_ref)
                else:
                    vigilancia = pendente or (
                        ultima if ultima and ultima.data_realizacao is None else
                        Vigilancia(estabelecimento=estabelecimento, ano_previsto=ano_ref)
                    )
                vigilancia.ano_previsto = ano_ref
                vigilancia.fiscal = fiscal
                vigilancia.data_realizacao = data_realizacao
                vigilancia.data_alvara = data_alvara
                vigilancia.inspecao_status = (
                    Vigilancia.Status.CONCLUIDO if data_realizacao else
                    request.POST.get('inspecao_status', vigilancia.inspecao_status)
                )
                if vigilancia.inspecao_status == Vigilancia.Status.CONCLUIDO and not data_realizacao:
                    raise ValidationError('Informe a data de realização da inspeção concluída.')
                mes = request.POST.get('mes_previsto', '').strip()
                vigilancia.mes_previsto = int(mes) if mes else None
                vigilancia.obs = texto_livre(request.POST.get('obs', request.POST.get('observacoes', vigilancia.obs)))
                for titulo, acao, status in InspecaoForm.acoes:
                    setattr(vigilancia, acao, inspecao_form.cleaned_data[acao])
                    setattr(vigilancia, status, inspecao_form.cleaned_data.get(status))
                vigilancia.full_clean()
                vigilancia.save()

            messages.success(request, 'Estabelecimento e histórico atualizados com sucesso!')
            return redirect(request.path)
        except ValidationError as erro:
            for mensagem in erro.messages:
                messages.error(request, mensagem)
        except (ValueError, OverflowError):
            messages.error(request, 'Confira os números e as datas informados.')

        # Recarrega os objetos: uma transação desfeita não restaura os objetos em memória.
        estabelecimento = get_object_or_404(_estabelecimentos_visiveis(request.user), pk=pk)
        vigilancia_exibir = estabelecimento.fiscalizacoes.select_related('fiscal').order_by('-id').first()

    return render(request, 'register/analisar.html', _contexto_analise(request, estabelecimento, pode_editar, form, inspecao_form))


@login_required
def cronograma_view(request):
    ano_atual = timezone.localdate().year
    fiscal_id = request.GET.get('fiscal', '')
    estabelecimentos = com_inspecao_atual(
        _estabelecimentos_visiveis(request.user), ano_atual,
    ).filter(status=False).order_by('numero_pasta', 'pk')
    if fiscal_id and fiscal_id != 'todos':
        if fiscal_id.isascii() and fiscal_id.isdigit() and len(fiscal_id) <= 18:
            estabelecimentos = estabelecimentos.filter(fiscal_atual_id=int(fiscal_id))
        else:
            estabelecimentos = estabelecimentos.none()

    estabelecimentos = list(estabelecimentos)
    ultimas = {}
    for vigilancia in Vigilancia.objects.filter(
        estabelecimento__in=estabelecimentos
    ).select_related('fiscal').order_by('estabelecimento_id', '-id'):
        ultimas.setdefault(vigilancia.estabelecimento_id, vigilancia)

    q1, q2, q3, sem_agendamento = [], [], [], []
    for estabelecimento in estabelecimentos:
        vigilancia = ultimas.get(estabelecimento.pk)
        mes = vigilancia.mes_previsto if vigilancia and vigilancia.ano_previsto == ano_atual else None
        realizada = vigilancia.data_realizacao if vigilancia else None
        if estabelecimento.status:
            status, status_class = 'CANCELADO', 'status-cancelado'
        elif estabelecimento.inspecao_status_atual == Vigilancia.Status.CONCLUIDO:
            status, status_class = 'REALIZADO', 'status-realizado'
        elif estabelecimento.inspecao_status_atual == Vigilancia.Status.PENDENTE:
            status, status_class = 'PENDENTE', 'status-pendente'
        else:
            status, status_class = 'A FAZER', 'status-afazer'
        item = {
            'estabelecimento': estabelecimento, 'vigilancia': vigilancia,
            'mes_previsto': mes, 'status': status, 'status_class': status_class,
            'ultima_inspecao': realizada,
            'pode_editar': request.user.is_superuser or estabelecimento.fiscal_atual_id == request.user.pk,
        }
        if mes in (1, 2, 3, 4):
            q1.append(item)
        elif mes in (5, 6, 7, 8):
            q2.append(item)
        elif mes in (9, 10, 11, 12):
            q3.append(item)
        else:
            sem_agendamento.append(item)

    return render(request, 'register/cronograma.html', {
        'q1': q1, 'q2': q2, 'q3': q3, 'sem_agendamento': sem_agendamento,
        'fiscais': _fiscais_visiveis(request.user),
        'fiscal_selecionado': fiscal_id, 'ano_atual': ano_atual,
    })


@login_required
@require_POST
def atualizar_mes_previsto_ajax(request):
    try:
        dados = json.loads(request.body)
        if not isinstance(dados, dict):
            raise ValueError
        estabelecimento_id = dados.get('estabelecimento_id')
        if not str(estabelecimento_id).isascii() or not str(estabelecimento_id).isdigit() or len(str(estabelecimento_id)) > 18:
            raise ValueError
        novo_mes = dados.get('mes_previsto')
        if novo_mes in (None, ''):
            mes = None
        elif isinstance(novo_mes, bool) or not str(novo_mes).isascii() or not str(novo_mes).isdigit():
            raise ValueError
        else:
            mes = int(novo_mes)
            if not 1 <= mes <= 12:
                raise ValueError
    except (ValueError, TypeError, UnicodeDecodeError):
        return JsonResponse({'sucesso': False, 'erro': 'Informe um estabelecimento válido e um mês entre 1 e 12, ou vazio.'}, status=400)

    with transaction.atomic():
        estabelecimento = _estabelecimentos_visiveis(request.user).select_for_update().filter(pk=int(estabelecimento_id)).first()
        if estabelecimento is None:
            return JsonResponse({'sucesso': False, 'erro': 'Estabelecimento não encontrado.'}, status=404)
        if not request.user.is_superuser and estabelecimento.fiscal_atual_id != request.user.pk:
            return JsonResponse({
                'sucesso': False,
                'erro': 'Você não tem permissão para alterar este estabelecimento.',
            }, status=403)
        vigilancia = estabelecimento.fiscalizacoes.order_by('-id').first()
        if vigilancia:
            vigilancia.mes_previsto = mes
            vigilancia.ano_previsto = timezone.localdate().year
            vigilancia.save(update_fields=['mes_previsto', 'ano_previsto', 'updated_at'])
        else:
            Vigilancia.objects.create(
                estabelecimento=estabelecimento, fiscal=request.user,
                ano_previsto=timezone.localdate().year, mes_previsto=mes,
                inspecao_status=Vigilancia.Status.A_FAZER,
            )
    return JsonResponse({'sucesso': True, 'mes_previsto': mes})


@login_required
def estatisticas_view(request):
    from .estatisticas_modulos import anos_modulos, metricas_modulos
    ano_atual = date.today().year
    estabelecimentos_visiveis = _estabelecimentos_visiveis(request.user)

    # 1. ANOS EXISTENTES NO BANCO
    anos_db = list(
        Vigilancia.objects.filter(estabelecimento__in=estabelecimentos_visiveis, ano_previsto__isnull=False)
        .values_list('ano_previsto', flat=True)
        .distinct()
        .order_by('-ano_previsto')
    )
    anos_realizados = Vigilancia.objects.filter(
        estabelecimento__in=estabelecimentos_visiveis,
        data_realizacao__isnull=False,
    ).dates('data_realizacao', 'year')
    anos_db = sorted(set(anos_db) | {data.year for data in anos_realizados} | anos_modulos(), reverse=True)
    if not anos_db:
        anos_db = [ano_atual]

    # CAPTURA DE FILTROS
    f_ano = request.GET.get('ano')
    try:
        f_ano = int(f_ano) if f_ano else anos_db[0]
        if not 1 <= f_ano <= 9999:
            raise ValueError
    except ValueError:
        f_ano = anos_db[0]

    f_fiscal = request.GET.get('fiscal', 'todos')
    f_risco = request.GET.get('risco', 'todos')
    f_quadrimestre = request.GET.get('quadrimestre', 'todos')
    f_mes = request.GET.get('mes', 'todos')
    f_classe = request.GET.get('classe', 'todas')

    # BASE: Apenas estabelecimentos ativos
    estabelecimentos_base = estabelecimentos_visiveis.filter(status=False)

    if f_fiscal != 'todos' and f_fiscal.isascii() and f_fiscal.isdigit() and len(f_fiscal) <= 18:
        estabelecimentos_base = estabelecimentos_base.filter(fiscal_atual_id=int(f_fiscal))

    estabelecimentos_com_risco = estabelecimentos_base
    if f_risco != 'todos':
        estabelecimentos_com_risco = estabelecimentos_base.filter(tipo_risco=f_risco)

    fiscais = _fiscais_visiveis(request.user)
    riscos_disponiveis = list(estabelecimentos_base.exclude(tipo_risco__isnull=True).exclude(tipo_risco='').values_list('tipo_risco', flat=True).distinct().order_by('tipo_risco'))
    classes_disponiveis = list(estabelecimentos_base.exclude(tipo_classe__isnull=True).exclude(tipo_classe='').values_list('tipo_classe', flat=True).distinct().order_by('tipo_classe'))

    # ----------------------------------------------------
    # 1. MÉTRICAS POR ANO
    # ----------------------------------------------------
    tot_ano = estabelecimentos_base.count()
    insp_ano = Vigilancia.objects.filter(
        estabelecimento__in=estabelecimentos_base,
        data_realizacao__year=f_ano
    ).values('estabelecimento').distinct().count()
    
    perc_ano = round((insp_ano / tot_ano * 100), 1) if tot_ano > 0 else 0.0

    metricas_ano = {
        'ano': f_ano,
        'total': tot_ano,
        'inspecionados': insp_ano,
        'nao_inspecionados': max(0, tot_ano - insp_ano),
        'percentual': perc_ano
    }

    # ----------------------------------------------------
    # 2. MÉTRICAS POR RISCO
    # ----------------------------------------------------
    metricas_risco = []
    riscos_query = list(estabelecimentos_base
                        .values_list('tipo_risco', flat=True).distinct())

    for r in sorted({risco for risco in riscos_query if risco}):
        if not r or (f_risco != 'todos' and str(r) != str(f_risco)):
            continue

        est_r = estabelecimentos_base.filter(tipo_risco=r)
        tot_r = est_r.count()
        insp_r = Vigilancia.objects.filter(
            estabelecimento__in=est_r,
            data_realizacao__year=f_ano
        ).values('estabelecimento').distinct().count()

        perc_r = round((insp_r / tot_r * 100), 1) if tot_r > 0 else 0.0

        metricas_risco.append({
            'risco': r,
            'total': tot_r,
            'inspecionados': insp_r,
            'percentual': perc_r
        })

    # ----------------------------------------------------
    # 3. MÉTRICAS POR QUADRIMESTRE
    # ----------------------------------------------------
    quads_map = {
        '1': ('1º', [1, 2, 3, 4]),
        '2': ('2º', [5, 6, 7, 8]),
        '3': ('3º', [9, 10, 11, 12])
    }

    metricas_quadrimestre = []
    tot_q_feito_geral = 0
    tot_q_afazer_geral = 0

    for q_key in ['1', '2', '3']:
        if f_quadrimestre != 'todos' and f_quadrimestre != q_key:
            continue

        q_label, q_meses = quads_map[q_key]
        vigilancias_q = Vigilancia.objects.filter(estabelecimento__in=estabelecimentos_com_risco)
        feito_q = vigilancias_q.filter(
            data_realizacao__year=f_ano, data_realizacao__month__in=q_meses,
        ).count()
        afazer_q = vigilancias_q.filter(
            data_realizacao__isnull=True, ano_previsto=f_ano, mes_previsto__in=q_meses,
        ).count()
        total_q = feito_q + afazer_q
        perc_q = round((feito_q / total_q * 100), 1) if total_q > 0 else 0.0

        metricas_quadrimestre.append({
            'quadrimestre': q_label,
            'total_afazer': afazer_q,
            'total_feito': feito_q,
            'percentual': perc_q
        })

        tot_q_feito_geral += feito_q
        tot_q_afazer_geral += afazer_q

    # ----------------------------------------------------
    # 4. MÉTRICAS POR MÊS
    # ----------------------------------------------------
    nomes_meses = [
        'JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO',
        'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'
    ]

    metricas_meses = []
    tot_m_feito_geral = 0
    tot_m_afazer_geral = 0

    for idx, m_nome in enumerate(nomes_meses, start=1):
        if f_mes != 'todos' and str(f_mes) != str(idx) and f_mes.upper() != m_nome:
            continue

        vigilancias_m = Vigilancia.objects.filter(estabelecimento__in=estabelecimentos_com_risco)
        feito_m = vigilancias_m.filter(
            data_realizacao__year=f_ano, data_realizacao__month=idx,
        ).count()
        afazer_m = vigilancias_m.filter(
            data_realizacao__isnull=True, ano_previsto=f_ano, mes_previsto=idx,
        ).count()
        total_m = feito_m + afazer_m
        perc_m = round((feito_m / total_m * 100), 1) if total_m > 0 else 0.0

        metricas_meses.append({
            'mes': m_nome,
            'total_afazer': afazer_m,
            'total_feito': feito_m,
            'percentual': perc_m
        })

        tot_m_feito_geral += feito_m
        tot_m_afazer_geral += afazer_m

    # ----------------------------------------------------
    # 5. MÉTRICAS POR CLASSE
    # ----------------------------------------------------
    metricas_classe = []
    inspecao_no_ano = Vigilancia.objects.filter(
        estabelecimento_id=OuterRef('pk'), data_realizacao__year=f_ano,
    )
    classes_query = estabelecimentos_base.exclude(
        tipo_classe__isnull=True,
    ).exclude(tipo_classe='')
    if f_classe != 'todas':
        classes_query = classes_query.filter(tipo_classe=f_classe)
    # Agrega no banco, sem executar duas consultas para cada classe.
    classes_query = classes_query.annotate(
        inspecionado_no_ano=Exists(inspecao_no_ano),
    ).order_by().values('tipo_classe').annotate(
        total=Count('pk'),
        inspecionados=Count('pk', filter=Q(inspecionado_no_ano=True)),
    )
    for item in classes_query:
        total = item['total']
        inspecionados = item['inspecionados']
        metricas_classe.append({
            'classe': item['tipo_classe'],
            'total': total,
            'inspecionados': inspecionados,
            'percentual': round(inspecionados / total * 100, 1) if total else 0.0,
        })

    metricas_classe = sorted(metricas_classe, key=lambda x: x['total'], reverse=True)

    # Conta estabelecimentos, não a quantidade de inspeções ou de pendências.
    # Mantém ativos e inativos; classe e fiscal correspondem ao cadastro atual.
    base_pendencias = estabelecimentos_visiveis
    if f_fiscal != 'todos' and f_fiscal.isascii() and f_fiscal.isdigit() and len(f_fiscal) <= 18:
        base_pendencias = base_pendencias.filter(fiscal_atual_id=int(f_fiscal))
    classes_pendencias = list(estabelecimentos_visiveis.exclude(
        tipo_classe__isnull=True,
    ).exclude(tipo_classe='').values_list('tipo_classe', flat=True).distinct().order_by('tipo_classe'))
    if f_classe != 'todas':
        base_pendencias = base_pendencias.filter(tipo_classe=f_classe)
    metricas_pendencias = []
    acoes_pendencias = [('plano', 'Plano de trabalho'), ('termo', 'Termo de ciência'),
                       ('interdicao', 'Interdição'), ('processo', 'Processo')]
    f_acao = request.GET.get('acao', 'todas')
    if f_acao not in dict(acoes_pendencias):
        f_acao = 'todas'
    for titulo, campo_aplicado, campo_status in (
        ('Plano de trabalho', 'plano_aplicado', 'plano_status'),
        ('Termo de ciência', 'termo_ciencia', 'termo_status'),
        ('Interdição', 'interdicao', 'interdicao_status'),
        ('Processo', 'processo', 'processo_status'),
    ):
        chave_acao = campo_status.removesuffix('_status')
        if f_acao != 'todas' and chave_acao != f_acao:
            continue
        conclusoes_posteriores = Vigilancia.objects.filter(
            estabelecimento_id=OuterRef('estabelecimento_id'),
            **{
                campo_aplicado: Vigilancia.Relatado.APLICADO,
                campo_status: Vigilancia.Status.CONCLUIDO,
            },
        ).filter(
            Q(data_realizacao__gt=OuterRef('data_realizacao'))
            | Q(data_realizacao=OuterRef('data_realizacao'), pk__gt=OuterRef('pk'))
        )
        totais = Vigilancia.objects.filter(
            estabelecimento__in=base_pendencias,
            data_realizacao__year=f_ano,
            **{
                campo_aplicado: Vigilancia.Relatado.APLICADO,
                campo_status: Vigilancia.Status.PENDENTE,
            },
        ).annotate(
            teve_conclusao_posterior=Exists(conclusoes_posteriores),
        ).aggregate(
            pendentes=Count('estabelecimento_id', distinct=True),
            concluidos=Count(
                'estabelecimento_id', distinct=True,
                filter=Q(teve_conclusao_posterior=True),
            ),
        )
        metricas_pendencias.append({
            'acao': titulo,
            'pendentes': totais['pendentes'],
            'concluidos': totais['concluidos'],
            'sem_conclusao': totais['pendentes'] - totais['concluidos'],
        })

    context = {
        'metricas_modulos': metricas_modulos(f_ano, str(f_fiscal), request.GET),
        'metricas_pendencias': metricas_pendencias,
        'acoes_pendencias': acoes_pendencias,
        'f_acao': f_acao,
        'total_estabelecimentos_pendencias': base_pendencias.count(),
        'classes_pendencias': classes_pendencias,
        'anos_disponiveis': anos_db,
        'fiscais': fiscais,
        'riscos_disponiveis': riscos_disponiveis,
        'classes_disponiveis': classes_disponiveis,
        'f_ano': f_ano,
        'f_fiscal': str(f_fiscal),
        'f_risco': str(f_risco),
        'f_quadrimestre': str(f_quadrimestre),
        'f_mes': str(f_mes),
        'f_classe': str(f_classe),
        'metricas_ano': metricas_ano,
        'metricas_risco': metricas_risco,
        'metricas_quadrimestre': metricas_quadrimestre,
        'metricas_meses': metricas_meses,
        'metricas_classe': metricas_classe,
        'chart_quad_totais': {'feito': tot_q_feito_geral, 'afazer': tot_q_afazer_geral},
        'chart_mes_totais': {'feito': tot_m_feito_geral, 'afazer': tot_m_afazer_geral},
    }

    return render(request, 'register/estatisticas.html', context)


@login_required
def baixar_documento_view(request, pk):
    documento = get_object_or_404(Documento, pk=pk)
    try:
        arquivo = documento.arquivo.open('rb')
    except (FileNotFoundError, ValueError):
        raise Http404('Arquivo não encontrado.')
    return FileResponse(arquivo, as_attachment=True, filename=documento.arquivo.name.rsplit('/', 1)[-1])
