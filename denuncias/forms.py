from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db.models import Q

from register.consultas import buscar_por_documento, endereco_estabelecimento, normalizar_documento
from .models import Denuncia


class DenunciaForm(forms.ModelForm):
    cadastro_id = forms.IntegerField(required=False, min_value=1, widget=forms.HiddenInput)

    class Meta:
        model = Denuncia
        fields = ('cnpj', 'razao_social', 'nome_fantasia', 'endereco', 'canal_entrada',
                  'tipo', 'motivo', 'data_denuncia', 'fiscal_responsavel',
                  'data_tratativa', 'medidas_adotadas', 'status')
        labels = {'cnpj': 'CNPJ / CPF', 'razao_social': 'Nome Empresarial (Razão Social)',
                  'nome_fantasia': 'Nome Fantasia', 'endereco': 'Endereço',
                  'canal_entrada': 'Canal de Entrada / Denunciante', 'tipo': 'Serviço ou Produto',
                  'motivo': 'Motivo da Denúncia', 'data_denuncia': 'Data da Denúncia',
                  'fiscal_responsavel': 'Fiscal Responsável', 'data_tratativa': 'Data da Tratativa / Inspeção',
                  'medidas_adotadas': 'Medidas Adotadas', 'status': 'Status'}
        widgets = {nome: forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})
                   for nome in ('data_denuncia', 'data_tratativa')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.estabelecimento = self.instance.estabelecimento if self.instance.pk else None
        self.erro_vinculo = None
        if self.estabelecimento is None:
            documento = self.data.get('cnpj') if self.is_bound else self.initial.get('cnpj')
            if documento:
                try:
                    self.estabelecimento = buscar_por_documento(documento)
                except ValidationError as error:
                    self.erro_vinculo = error
        if self.estabelecimento:
            # Mantém a fotografia da denúncia existente; novas denúncias usam o cadastro.
            est = self.estabelecimento
            valores = ({campo: getattr(self.instance, campo) for campo in self.Meta.fields[:4]}
                       if self.instance.pk and self.instance.estabelecimento_id else
                       {'cnpj': est.cnpj, 'razao_social': est.razao_social,
                        'nome_fantasia': est.nome_fantasia, 'endereco': endereco_estabelecimento(est)})
            for campo, valor in valores.items():
                self.initial[campo] = valor
                self.fields[campo].disabled = True
        self.fields['fiscal_responsavel'].queryset = get_user_model().objects.filter(
            Q(is_active=True) | Q(pk=self.instance.fiscal_responsavel_id)
        ).order_by('first_name', 'username')
        for name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs['rows'] = 3
                field.max_length = 10000
                field.validators.append(MaxLengthValidator(10000))
                field.widget.attrs['maxlength'] = 10000

    @property
    def sections(self):
        return [
            ('Dados do Estabelecimento', [self[name] for name in self.Meta.fields[:4]]),
            ('Dados da Denúncia', [self[name] for name in self.Meta.fields[4:]]),
        ]

    def clean(self):
        dados = super().clean()
        if self.erro_vinculo:
            raise self.erro_vinculo
        cnpj = dados.get('cnpj')
        if not cnpj:
            return dados
        # Preserva o vínculo existente; só a criação determina o estabelecimento.
        if self.instance.pk and self.instance.estabelecimento_id:
            if normalizar_documento(cnpj) != normalizar_documento(self.instance.cnpj):
                raise ValidationError('Não altere o documento de uma denúncia já vinculada.')
        if dados.get('cadastro_id') and (not self.estabelecimento or self.estabelecimento.pk != dados['cadastro_id']):
            raise ValidationError('O estabelecimento não corresponde ao CNPJ/CPF informado.')
        if dados.get('data_denuncia') and dados.get('data_tratativa') and dados['data_tratativa'] < dados['data_denuncia']:
            self.add_error('data_tratativa', 'A tratativa não pode ser anterior à denúncia.')
        return dados
