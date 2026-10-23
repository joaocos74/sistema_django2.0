from uuid import uuid4
import unicodedata

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models


def chave_classe(nome):
    texto = ''.join(c for c in unicodedata.normalize('NFKD', nome.casefold())
                    if not unicodedata.combining(c))
    chave = ' '.join(texto.split())
    # Equivalência solicitada para a classificação desta biblioteca.
    return {'servicos de alimentos': 'alimentos'}.get(chave, chave)


class ClasseResolucao(models.Model):
    nome = models.CharField('Nome', max_length=120)
    chave = models.CharField(max_length=240, unique=True, editable=False)

    class Meta:
        ordering = ['nome', 'pk']
        verbose_name = 'Classe de resolução'
        verbose_name_plural = 'Classes de resoluções'

    def save(self, *args, **kwargs):
        self.nome = ' '.join(self.nome.split())
        self.chave = chave_classe(self.nome)
        if self.chave == 'alimentos':
            self.nome = 'Alimentos'
        if kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = set(kwargs['update_fields']) | {'nome', 'chave'}
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


def armazenamento_privado():
    return FileSystemStorage(location=settings.RESOLUCOES_ROOT)


def caminho_resolucao(instance, filename):
    return f'{uuid4().hex}.pdf'


class Resolucao(models.Model):
    descricao = models.CharField('Descrição', max_length=255)
    revogada = models.BooleanField('Resolução revogada', default=False)
    classe = models.ForeignKey(ClasseResolucao, on_delete=models.PROTECT, null=True, blank=True,
                               related_name='resolucoes', verbose_name='Classe')
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
