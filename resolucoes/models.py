from uuid import uuid4

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models


def armazenamento_privado():
    return FileSystemStorage(location=settings.RESOLUCOES_ROOT)


def caminho_resolucao(instance, filename):
    return f'{uuid4().hex}.pdf'


class Resolucao(models.Model):
    descricao = models.CharField('Descrição', max_length=255)
    revogada = models.BooleanField('Resolução revogada', default=False)
    arquivo = models.FileField('Arquivo PDF', upload_to=caminho_resolucao, storage=armazenamento_privado)
    nome_original = models.CharField(max_length=255, editable=False)
    tamanho = models.PositiveBigIntegerField(editable=False)
    adicionado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                      related_name='resolucoes_adicionadas')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em', '-pk']
        verbose_name = 'Resolução'
        verbose_name_plural = 'Resoluções'

    def __str__(self):
        return self.descricao
