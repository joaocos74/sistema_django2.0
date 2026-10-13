from django.db import models
from django.contrib.auth.models import User
from register.models import Estabelecimento

class Denuncia(models.Model):
    criado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='denuncias_registradas')
    atualizado_em = models.DateTimeField(auto_now=True)
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('em_andamento', 'Em Andamento'),
        ('concluido', 'Concluído'),
    ]

    TIPO_CHOICES = [
        ('Serviço', 'Serviço'),
        ('Produto', 'Produto'),
    ]

    estabelecimento = models.ForeignKey(
        Estabelecimento, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='denuncias'
    )
    cnpj = models.CharField(max_length=30)
    razao_social = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255, blank=True, null=True)
    endereco = models.TextField(blank=True, null=True)
    
    canal_entrada = models.CharField(max_length=255, blank=True, null=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, blank=True, null=True)
    motivo = models.TextField(blank=True, null=True)
    data_denuncia = models.DateField(null=True, blank=True)
    
    fiscal_responsavel = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='denuncias_designadas'
    )
    data_tratativa = models.DateField(null=True, blank=True)
    medidas_adotadas = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pendente')
    
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_criacao']
        verbose_name = 'Denúncia'
        verbose_name_plural = 'Denúncias'

    def __str__(self):
        return f"Denúncia #{self.id} - {self.razao_social}"

    @property
    def nome_fiscal(self):
        if not self.fiscal_responsavel:
            return '—'
        return self.fiscal_responsavel.get_full_name() or self.fiscal_responsavel.username
