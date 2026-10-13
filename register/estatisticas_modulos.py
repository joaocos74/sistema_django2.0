from django.db.models import Count, Q, DateField
from django.db.models.functions import Cast, Coalesce
from django.utils import timezone

from denuncias.models import Denuncia
from redesim.models import RegistroRedesim


MESES = ('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
         'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro')


def denuncias_com_data():
    return Denuncia.objects.annotate(data_referencia=Coalesce(
        'data_denuncia', Cast('data_criacao', DateField()), output_field=DateField(),
    ))


def anos_modulos():
    return ({timezone.localdate().year}
            | {data.year for data in denuncias_com_data().dates('data_referencia', 'year')}
            | {data.year for data in RegistroRedesim.objects.dates('data_liberacao', 'year')})


def metricas_modulos(ano, fiscal, parametros=None):
    parametros = parametros or {}
    from django.contrib.auth import get_user_model
    anos = sorted(anos_modulos() | {ano}, reverse=True)
    usuarios = [('todos', 'Todos'), ('sem_fiscal', 'Sem fiscal')] + [
        (str(user.pk), user.get_full_name() or user.username)
        for user in get_user_model().objects.order_by('first_name', 'username')
    ]
    meses = [('todos', 'Todos')] + [(str(i), nome) for i, nome in enumerate(MESES, 1)]
    filtros = {}

    def filtro(modulo, chave, label, opcoes, padrao='todos'):
        nome = f'{modulo}_{chave}'
        valor = str(parametros.get(nome, padrao))
        if valor not in {str(v) for v, _ in opcoes}:
            valor = str(padrao) if str(padrao) in {str(v) for v, _ in opcoes} else str(opcoes[0][0])
        filtros.setdefault(modulo, []).append({'nome': nome, 'label': label, 'valor': valor,
            'opcoes': [{'valor': str(v), 'label': texto} for v, texto in opcoes]})
        return valor

    def periodo(modulo, queryset, campo_data, campo_fiscal):
        ano_escolhido = filtro(modulo, 'ano', 'Ano', [(str(a), str(a)) for a in anos], str(ano))
        mes = filtro(modulo, 'mes', 'Mês', meses)
        responsavel = filtro(modulo, 'fiscal', 'Fiscal', usuarios, fiscal)
        queryset = queryset.filter(**{f'{campo_data}__year': int(ano_escolhido)})
        if mes != 'todos':
            queryset = queryset.filter(**{f'{campo_data}__month': int(mes)})
        if responsavel == 'sem_fiscal':
            queryset = queryset.filter(**{f'{campo_fiscal}__isnull': True})
        elif responsavel != 'todos':
            queryset = queryset.filter(**{f'{campo_fiscal}_id': int(responsavel)})
        rotulo = ano_escolhido if mes == 'todos' else f'{MESES[int(mes) - 1]} / {ano_escolhido}'
        return queryset, rotulo

    denuncias, periodo_den = periodo('denuncias', denuncias_com_data(), 'data_referencia', 'fiscal_responsavel')
    tipo = filtro('denuncias', 'tipo', 'Tipo', [('todos', 'Todos'), ('Produto', 'Produto'), ('Serviço', 'Serviço'), ('sem_tipo', 'Sem tipo')])
    status = filtro('denuncias', 'status', 'Status', [('todos', 'Todos')] + Denuncia.STATUS_CHOICES)
    if tipo == 'sem_tipo':
        denuncias = denuncias.filter(Q(tipo='') | Q(tipo__isnull=True))
    elif tipo != 'todos':
        denuncias = denuncias.filter(tipo=tipo)
    if status != 'todos':
        denuncias = denuncias.filter(status=status)

    redesim, periodo_red = periodo('redesim', RegistroRedesim.objects.all(), 'data_liberacao', 'fiscal')
    classes = RegistroRedesim.objects.exclude(classe='').order_by('classe').values_list('classe', flat=True).distinct()
    niveis = RegistroRedesim.objects.exclude(nivel='').order_by('nivel').values_list('nivel', flat=True).distinct()
    classe = filtro('redesim', 'classe', 'Classe', [('todos', 'Todas'), ('sem_classe', 'Não informada')] + [(c, c) for c in classes])
    mapa_risco = {'NIVEL 1': 'Risco I', 'NIVEL 2': 'Risco II', 'NIVEL 3': 'Risco III', 'NIVEL 4': 'Risco IV'}
    risco = filtro('redesim', 'risco', 'Risco', [('todos', 'Todos'), ('sem_risco', 'Não informado')] + [(n, mapa_risco.get(n, n)) for n in niveis])
    if classe != 'todos':
        redesim = redesim.filter(classe='' if classe == 'sem_classe' else classe)
    if risco != 'todos':
        redesim = redesim.filter(nivel='' if risco == 'sem_risco' else risco)

    contagens = dict(
        total=Count('pk'),
        pendente=Count('pk', filter=Q(status='pendente')),
        em_andamento=Count('pk', filter=Q(status='em_andamento')),
        concluido=Count('pk', filter=Q(status='concluido')),
        produtos=Count('pk', filter=Q(tipo='Produto')),
        servicos=Count('pk', filter=Q(tipo='Serviço')),
        sem_tipo=Count('pk', filter=Q(tipo='') | Q(tipo__isnull=True)),
    )
    colunas_den = ['Total', 'Pendentes', 'Em andamento', 'Concluídas', 'Produtos', 'Serviços', 'Sem tipo']
    series_den = [
        {'chave': 'pendente', 'nome': 'Pendentes', 'cor': '#d97706'},
        {'chave': 'em_andamento', 'nome': 'Em andamento', 'cor': '#2563eb'},
        {'chave': 'concluido', 'nome': 'Concluídas', 'cor': '#169b5b'},
    ]
    ajuda_den = ('Ano e mês usam a data da denúncia; quando não informada, usam a data de criação. '
                 'O fiscal é o responsável pela denúncia. Status refletem a situação atual. '
                 'Inclui denúncias sem estabelecimento vinculado.')
    cards = []

    def card(id, titulo, headers, itens, chaves, series, ajuda):
        cards.append({'id': id, 'titulo': titulo, 'headers': headers,
                      'linhas': [[item['rotulo']] + [item[chave] for chave in chaves] for item in itens],
                      'itens': itens, 'series': series, 'ajuda': ajuda})

    totais = denuncias.aggregate(**contagens)
    card('denuncias', 'Denúncias', ['Período'] + colunas_den,
         [{'rotulo': periodo_den, **totais}], list(contagens), series_den, ajuda_den)

    contagens_red = {'liberacoes': Count('pk')}
    series_red = [{'chave': 'liberacoes', 'nome': 'Liberados', 'cor': '#169b5b'}]
    ajuda_red = ('Ano e mês usam a Data da Liberação. Lançamentos sem essa data ficam fora da contagem. '
                 'O fiscal é o usuário que registrou a liberação. Classe e risco são os guardados no lançamento. '
                 'Cada lançamento de liberação conta uma vez, conforme os filtros selecionados.')
    card('redesim', 'Redesim', ['Período', 'Liberados'],
         [{'rotulo': periodo_red, **redesim.aggregate(**contagens_red)}], list(contagens_red), series_red, ajuda_red)
    for item in cards:
        item['filtros'] = filtros[item['id']]
        item['preservados'] = [
            {'nome': f['nome'], 'valor': f['valor']}
            for modulo, campos in filtros.items() if modulo != item['id'] for f in campos
        ]
        item['preservados'] += [{'nome': chave, 'valor': valor} for chave, valor in parametros.items()
                               if chave in ('ano', 'fiscal', 'mes', 'risco', 'classe', 'quadrimestre', 'acao')]
    return cards
