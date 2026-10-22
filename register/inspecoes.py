"""Situação anual da inspeção mais recente, comum às telas de consulta."""
from django.db.models import Case, CharField, OuterRef, Subquery, Value, When
from django.utils import timezone

from .models import Vigilancia


def com_inspecao_atual(estabelecimentos, ano=None):
    ano = ano if ano is not None else timezone.localdate().year
    ultima = Vigilancia.objects.filter(estabelecimento_id=OuterRef('pk')).order_by('-pk')
    campos = {
        'inspecao_atual_id': 'pk', 'inspecao_fiscal_id': 'fiscal_id',
        'inspecao_realizada_em': 'data_realizacao', 'inspecao_alvara_em': 'data_alvara',
        'inspecao_ano_previsto': 'ano_previsto', 'inspecao_mes_previsto': 'mes_previsto',
        'inspecao_status_gravado': 'inspecao_status',
    }
    return estabelecimentos.annotate(**{
        nome: Subquery(ultima.values(campo)[:1]) for nome, campo in campos.items()
    }).annotate(inspecao_status_atual=Case(
        When(inspecao_realizada_em__year=ano, then=Value(Vigilancia.Status.CONCLUIDO)),
        When(inspecao_status_gravado=Vigilancia.Status.PENDENTE, then=Value(Vigilancia.Status.PENDENTE)),
        default=Value(Vigilancia.Status.A_FAZER), output_field=CharField(),
    ))
