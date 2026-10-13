from django.conf import settings
from django.db import models

from register.models import Estabelecimento


class RegistroRedesim(models.Model):
    estabelecimento = models.ForeignKey(
        Estabelecimento,
        on_delete=models.PROTECT,
        related_name="registros_redesim",
    )

    # Usuário que realizou o lançamento no sistema.
    # Mantive o nome "fiscal" porque esse campo já existe no banco atual.
    fiscal = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_redesim_realizados",
    )

    # ============================================================
    # SNAPSHOT
    # Guarda exatamente os dados existentes no momento da REDESIM.
    # Isso reproduz o comportamento da tabela REDESIM do Flask.
    # ============================================================

    razao_social = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    nome_fantasia = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    cnpj_cpf = models.CharField(
        max_length=18,
        blank=True,
        default="",
        db_index=True,
    )

    nivel = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    classe = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    cnae_principal = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    fiscal_responsavel = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    fiscal_matricula = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    data_liberacao = models.DateField(
        null=True,
        blank=True,
    )

    observacoes = models.TextField(
        blank=True,
        default="",
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-id"]
        verbose_name = "Registro REDESIM"
        verbose_name_plural = "Registros REDESIM"

    def __str__(self):
        nome = self.razao_social or self.estabelecimento.razao_social
        return f"REDESIM - {nome}"