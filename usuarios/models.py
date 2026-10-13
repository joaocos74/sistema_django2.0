from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

PALETA_CORES = ('#fef08a', '#bbf7d0', '#bfdbfe', '#fbcfe8', '#fed7aa', '#e9d5ff')


class PerfilUsuario(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil')
    cor = models.CharField(max_length=7, default='#fef08a', validators=[
        RegexValidator(r'^#[0-9a-fA-F]{6}$', 'Informe uma cor hexadecimal válida.'),
    ])

    def __str__(self):
        return str(self.user)
