from pathlib import Path

from django import forms
from django.conf import settings

from .models import Resolucao


class ResolucaoForm(forms.ModelForm):
    class Meta:
        model = Resolucao
        fields = ['arquivo', 'descricao']
        widgets = {
            'arquivo': forms.FileInput(attrs={'accept': '.pdf,application/pdf', 'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Ex.: RDC nº 216/2004 — Boas práticas para serviços de alimentação',
            }),
        }

    def clean_arquivo(self):
        arquivo = self.cleaned_data['arquivo']
        if arquivo.size > settings.RESOLUCOES_MAX_BYTES:
            raise forms.ValidationError('O PDF ultrapassa o tamanho máximo permitido.')
        if Path(arquivo.name).suffix.lower() != '.pdf':
            raise forms.ValidationError('Selecione um arquivo PDF para visualizar no navegador.')
        assinatura = arquivo.read(5)
        arquivo.seek(0)
        if assinatura != b'%PDF-':
            raise forms.ValidationError('O arquivo enviado não possui a identificação de um PDF.')
        return arquivo


class EditarResolucaoForm(forms.ModelForm):
    class Meta:
        model = Resolucao
        fields = ['descricao', 'revogada']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
        }
