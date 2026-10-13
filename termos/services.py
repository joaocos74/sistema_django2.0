import time

from django.db import transaction, OperationalError
from django.db.models import F
from django.utils import timezone

from .models import SequenciaNotificacao, NotificacaoEmitida, NotificacaoPadrao


def proximo_numero():
    ano = timezone.localdate().year
    ultimo = SequenciaNotificacao.objects.filter(ano=ano).values_list('ultimo_numero', flat=True).first() or 0
    return f'{ultimo + 1:02d}/{ano}'


def gerar_notificacao(est, user, campos, chave):
    # Retry limitado para concorrência de escrita no SQLite. Todos os efeitos são atômicos.
    for tentativa in range(5):
        try:
            with transaction.atomic():
                ano = timezone.localdate().year
                SequenciaNotificacao.objects.get_or_create(ano=ano)
                # UPDATE adquire trava de escrita também no SQLite (select_for_update é ignorado nele).
                SequenciaNotificacao.objects.filter(ano=ano).update(ultimo_numero=F('ultimo_numero') + 1)
                existente = NotificacaoEmitida.objects.filter(chave=chave).first()
                if existente:
                    SequenciaNotificacao.objects.filter(ano=ano).update(ultimo_numero=F('ultimo_numero') - 1)
                    return existente
                numero = SequenciaNotificacao.objects.get(ano=ano).ultimo_numero
                registro = NotificacaoEmitida.objects.create(estabelecimento=est, gerado_por=user,
                    ano=ano, numero=numero, campos=campos, chave=chave)
                NotificacaoPadrao.objects.update_or_create(estabelecimento=est,
                    defaults={'campos': campos, 'atualizado_por': user})
                return registro
        except OperationalError as exc:
            if 'locked' not in str(exc).lower() or tentativa == 4:
                raise
            time.sleep(0.1 * (tentativa + 1))
