"""Numeração da pasta física independente das chaves e vínculos do cadastro."""
from django.core.exceptions import ValidationError
from django.db import models, router, transaction


def validar_numero_pasta(est, using=None):
    from .models import Estabelecimento
    numero = est.numero_pasta
    if numero is None:
        if not est._state.adding:
            raise ValidationError('Informe o número da pasta.')
        return
    if not isinstance(numero, int) or isinstance(numero, bool) or not 1 <= numero <= 9223372036854775807:
        raise ValidationError('Informe um número de pasta inteiro e positivo.')
    if not est.status and Estabelecimento.objects.using(using).filter(
        numero_pasta=numero, status=False,
    ).exclude(pk=est.pk).exists():
        raise ValidationError(f'A pasta {numero} já pertence a um estabelecimento ativo. Escolha outra pasta antes de ativar ou salvar.')


def salvar_estabelecimento(est, args, kwargs, usuario):
    from .models import Estabelecimento, HistoricoPasta, SequenciaPasta
    using = kwargs.get('using') or router.db_for_write(Estabelecimento, instance=est)
    with transaction.atomic(using=using):
        anterior = None
        if not est._state.adding:
            anterior = Estabelecimento.objects.using(using).select_for_update().get(pk=est.pk)
        campos = kwargs.get('update_fields')
        if campos is not None:
            # Audita somente valores efetivamente gravados por save(update_fields=...).
            if not campos:
                return
            if anterior:
                for nome in ('numero_pasta', 'status'):
                    if nome not in campos:
                        setattr(est, nome, getattr(anterior, nome))
        sequencias = SequenciaPasta.objects.using(using)
        sequencias.get_or_create(pk=1)
        # A atualização também serializa a reserva no SQLite usado em testes locais.
        sequencias.filter(pk=1).update(ultimo_numero=models.F('ultimo_numero'))
        sequencia = sequencias.get(pk=1)
        if est._state.adding and est.numero_pasta is None:
            maior_ativo = Estabelecimento.objects.using(using).filter(status=False).aggregate(
                numero=models.Max('numero_pasta'),
            )['numero'] or 0
            est.numero_pasta = maior_ativo + 1
        # O maior número histórico permanece apenas como registro. A próxima pasta
        # é calculada pelos ativos, sob o bloqueio acima para evitar reservas iguais.
        validar_numero_pasta(est, using)
        if est.numero_pasta > sequencia.ultimo_numero:
            sequencias.filter(pk=1).update(ultimo_numero=est.numero_pasta)
        models.Model.save(est, *args, **kwargs)
        if anterior is None or (anterior.numero_pasta, anterior.status) != (est.numero_pasta, est.status):
            HistoricoPasta.objects.using(using).create(
                estabelecimento=est, numero_anterior=anterior.numero_pasta if anterior else None,
                numero_novo=est.numero_pasta, inativo_anterior=anterior.status if anterior else None,
                inativo_novo=est.status, alterado_por=usuario,
            )
