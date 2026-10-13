from django.conf import settings
from django.db import models


class ItemAgenda(models.Model):
    class Turno(models.TextChoices):
        MANHA = 'manha', 'Manhã'
        TARDE = 'tarde', 'Tarde'

    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='itens_agenda')
    dia = models.DateField(db_index=True)
    turno = models.CharField(max_length=10, choices=Turno.choices, default=Turno.MANHA)
    texto = models.TextField(max_length=3000)
    feito = models.BooleanField(default=False)
    mencionados = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='mencoes_agenda')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['dia', 'turno', 'pk']

    def __str__(self):
        return f'{self.dia} — {self.autor}'
