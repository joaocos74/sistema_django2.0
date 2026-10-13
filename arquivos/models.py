from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models


def armazenamento_privado():
    return FileSystemStorage(location=settings.ARQUIVOS_ROOT)


def caminho_arquivo(instance, filename):
    return f'{uuid4().hex}{Path(filename).suffix.lower()[:20]}'


class Arquivo(models.Model):
    nome = models.CharField('Nome', max_length=255)
    descricao = models.TextField('Descrição', blank=True)
    arquivo = models.FileField('Arquivo', upload_to=caminho_arquivo, storage=armazenamento_privado)
    nome_original = models.CharField(max_length=255, editable=False)
    tamanho = models.PositiveBigIntegerField(editable=False)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name='arquivos_gerais_enviados')
    data_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_envio', '-pk']
        verbose_name = 'Arquivo geral'
        verbose_name_plural = 'Arquivos gerais'

    def __str__(self):
        return self.nome
