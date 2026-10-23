from pathlib import Path

from django import forms
from django.conf import settings

from .models import Resolucao, ClasseResolucao, chave_classe


class ClassificacaoForm(forms.ModelForm):
    nova_classe = forms.CharField(label='Nome da nova classe', max_length=120, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Confira a lista antes de criar uma classe'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.classes = {str(classe.pk): classe for classe in ClasseResolucao.objects.all()}
        self.fields['classe'] = forms.ChoiceField(label='Classe', required=False,
            choices=[('', 'Selecione uma classe')] + [(pk, classe.nome) for pk, classe in self.classes.items()]
                    + [('nova', '+ Cadastrar nova classe')],
            widget=forms.Select(attrs={'class': 'form-control', 'data-classe-select': ''}))
        if self.instance.pk and self.instance.classe_id:
            self.initial['classe'] = str(self.instance.classe_id)
        self.novo_nome = None

    def clean(self):
        dados = super().clean()
        escolha = dados.get('classe')
        nome = ' '.join((dados.get('nova_classe') or '').split())
        if escolha == 'nova':
            if not nome or not chave_classe(nome):
                self.add_error('nova_classe', 'Informe o nome da nova classe.')
            else:
                self.novo_nome = nome
            dados['classe'] = None
        elif escolha in self.classes:
            dados['classe'] = self.classes[escolha]
            if nome:
                self.add_error('nova_classe', 'Selecione “Cadastrar nova classe” ou limpe o nome informado.')
        else:
            dados['classe'] = None
            if 'classe' not in self.errors:
                self.add_error('classe', 'Selecione uma classe existente ou cadastre uma nova.')
        return dados

    def save(self, commit=True):
        # A view envolve a gravação da classe e da resolução na mesma transação.
        if not self.is_valid():
            raise ValueError('Não é possível salvar um formulário inválido.')
        if self.novo_nome:
            self.instance.classe, _ = ClasseResolucao.objects.get_or_create(
                chave=chave_classe(self.novo_nome), defaults={'nome': self.novo_nome})
        return super().save(commit=commit)


class ResolucaoForm(ClassificacaoForm):
    class Meta:
        model = Resolucao
        fields = ['arquivo', 'descricao', 'classe']
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


class EditarResolucaoForm(ClassificacaoForm):
    class Meta:
        model = Resolucao
        fields = ['descricao', 'classe', 'revogada']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
        }


class FiltroResolucaoForm(forms.Form):
    q = forms.CharField(label='Pesquisar resoluções', required=False, max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'search',
                                     'placeholder': 'Descrição ou nome do arquivo'}))
    classe = forms.ChoiceField(label='Classe', required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    situacao = forms.ChoiceField(label='Situação', required=False, choices=[
        ('', 'Todas'), ('nao_revogadas', 'Não revogadas'), ('revogadas', 'Revogadas')],
        widget=forms.Select(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['classe'].choices = [('', 'Todas as classes'), ('sem_classe', 'Sem classe')] + [
            (str(classe.pk), classe.nome) for classe in ClasseResolucao.objects.all()]
