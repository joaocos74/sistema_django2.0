from django import forms
from django.conf import settings
from .models import Arquivo


class ArquivoForm(forms.ModelForm):
    class Meta:
        model = Arquivo
        fields = ['nome', 'descricao', 'arquivo']
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Ex.: Modelo de relatório'}),
            'descricao': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Descrição opcional'}),
        }

    def clean_arquivo(self):
        arquivo = self.cleaned_data['arquivo']
        if arquivo.size > settings.ARQUIVOS_MAX_BYTES:
            raise forms.ValidationError('O arquivo ultrapassa o tamanho máximo permitido.')
        return arquivo
