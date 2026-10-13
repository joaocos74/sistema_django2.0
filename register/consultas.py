import re

from django.core.exceptions import ValidationError
from django.db.models import F, Value
from django.db.models.functions import Replace

from .models import Estabelecimento


def normalizar_documento(valor):
    return re.sub(r'[.\-/\s]', '', valor or '').upper()


def buscar_por_documento(documento, bloquear=False):
    documento = normalizar_documento(documento)
    if not documento or len(documento) > 18:
        raise ValidationError('Informe um CNPJ/CPF válido para a pesquisa.')
    from django.db.models.functions import Upper
    expressao = Upper(F('cnpj'))
    for sinal in ('.', '/', '-', ' '):
        expressao = Replace(expressao, Value(sinal), Value(''))
    consulta = Estabelecimento.objects.annotate(documento_busca=expressao).filter(documento_busca=documento)
    if bloquear:
        consulta = consulta.select_for_update()
    resultados = list(consulta.order_by('pk')[:2])
    if len(resultados) > 1:
        raise ValidationError('Há mais de um estabelecimento com este CNPJ/CPF. Regularize os cadastros antes de vincular.')
    return resultados[0] if resultados else None


def endereco_estabelecimento(estabelecimento):
    return ', '.join(str(valor) for valor in (
        estabelecimento.logradouro, estabelecimento.numero, estabelecimento.bairro,
        estabelecimento.cidade, estabelecimento.uf,
    ) if valor)
