from django.conf import settings
from django.db import models


class SequenciaNotificacao(models.Model):
    ano = models.PositiveIntegerField(primary_key=True)
    ultimo_numero = models.PositiveIntegerField(default=0)


class NotificacaoEmitida(models.Model):
    estabelecimento = models.ForeignKey('register.Estabelecimento', on_delete=models.PROTECT, related_name='notificacoes_emitidas')
    ano = models.PositiveIntegerField()
    numero = models.PositiveIntegerField()
    campos = models.JSONField(default=dict)
    chave = models.UUIDField(unique=True)
    gerado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    gerado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-ano', '-numero']
        constraints = [models.UniqueConstraint(fields=['ano', 'numero'], name='notificacao_numero_anual_unico')]

    @property
    def numero_formatado(self):
        return f'{self.numero:02d}/{self.ano}'

class AutoTermoPadrao(models.Model):
    estabelecimento = models.OneToOneField("register.Estabelecimento", on_delete=models.CASCADE, related_name='auto_termo_padrao')
    campos = models.JSONField(default=dict)
    atualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='padroes_auto_termo')
    atualizado_em = models.DateTimeField(auto_now=True)


    class Meta:
        db_table = "register_autotermopadrao"


class NotificacaoPadrao(models.Model):
    estabelecimento = models.OneToOneField("register.Estabelecimento", on_delete=models.CASCADE, related_name='notificacao_padrao')
    campos = models.JSONField(default=dict)
    atualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='padroes_notificacao')
    atualizado_em = models.DateTimeField(auto_now=True)


    class Meta:
        db_table = "register_notificacaopadrao"
