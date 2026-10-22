from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Estabelecimento, Responsavel, RTResponsavel, Tipo, Vigilancia


class NumeroPastaForm(forms.Form):
    numero_pasta = forms.IntegerField(
        label='Número da pasta', min_value=1, max_value=9223372036854775807,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
    )


class EstabelecimentoForm(forms.ModelForm):
    # Mantém os nomes de endereço já usados pela view de cadastro.
    campos_estab = (
        'logradouro', 'numero', 'bairro', 'cidade', 'uf', 'cep', 'phone', 'email',
    )
    campos_tipo = ('cnae_principal', 'cnae_secundaria', 'classe', 'risco')
    campos_responsavel = (
        'nome', 'cpf', 'rg', 'nacionalidade', 'naturalidade', 'estado_civil',
        'profissao', 'phone', 'logradouro', 'numero', 'bairro', 'cidade', 'uf',
    )
    campos_rt = campos_responsavel + ('rg_conselho',)

    class Meta:
        model = Estabelecimento
        fields = (
            'razao_social', 'nome_fantasia', 'cnpj', 'n_parecer', 'logradouro',
            'numero', 'bairro', 'cidade', 'uf', 'cep', 'phone', 'email',
            'insc_municipal', 'latitude', 'longitude',
        )
        labels = {'phone': 'Telefone', 'insc_municipal': 'Inscrição municipal'}

    def add_prefix(self, field_name):
        if field_name in self.campos_estab:
            field_name = f'estab_{field_name}'
        return super().add_prefix(field_name)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        for model, campos, prefixo in (
            (Tipo, self.campos_tipo, ''),
            (Responsavel, self.campos_responsavel, 'resp_'),
            (RTResponsavel, self.campos_rt, 'rt_'),
        ):
            for nome in campos:
                field = model._meta.get_field(nome).formfield()
                field.required_on_fill = prefixo == 'resp_' and field.required
                if prefixo:
                    # Responsável é validado quando a seção é preenchida; RT é opcional.
                    field.required = False
                field.label = {
                    'phone': 'Telefone', 'rg_conselho': 'Conselho / Inscrição',
                    'cnae_principal': 'CNAE principal', 'cnae_secundaria': 'CNAE secundária',
                    'cpf': 'CPF', 'rg': 'RG', 'uf': 'UF',
                }.get(nome, field.label)
                self.fields[f'{prefixo}{nome}'] = field

        self.fields['fiscal_responsavel'] = forms.ModelChoiceField(
            label='Fiscal responsável', queryset=get_user_model().objects.none(),
            empty_label='Selecione o fiscal responsável',
        )
        if user is not None and user.is_authenticated:
            fiscais = get_user_model().objects.filter(is_active=True)
            if not user.is_superuser:
                fiscais = fiscais.filter(pk=user.pk)
                self.fields['fiscal_responsavel'].disabled = True
            self.fields['fiscal_responsavel'].queryset = fiscais.order_by('first_name', 'username')
            self.fields['fiscal_responsavel'].initial = user.pk

        self.fields['cidade'].initial = 'Taiobeiras'
        self.fields['uf'].initial = 'MG'
        labels = {
            'razao_social': 'Razão social', 'nome_fantasia': 'Nome fantasia',
            'cnpj': 'CNPJ / CPF', 'n_parecer': 'Número do parecer',
            'logradouro': 'Endereço / Logradouro', 'numero': 'Número',
            'uf': 'UF', 'cep': 'CEP', 'phone': 'Telefone', 'email': 'E-mail',
            'insc_municipal': 'Inscrição municipal', 'profissao': 'Profissão',
            'estado_civil': 'Estado civil', 'cpf': 'CPF', 'rg': 'RG',
            'rg_conselho': 'Conselho / Inscrição',
        }
        placeholders = {
            'razao_social': 'Ex.: Mercado Exemplo Ltda.',
            'nome_fantasia': 'Ex.: Mercado Exemplo',
            'cnpj': 'Informe o CNPJ ou CPF',
            'n_parecer': 'Ex.: 001/2026',
            'logradouro': 'Ex.: Rua Principal',
            'numero': 'Ex.: 123 ou S/N',
            'bairro': 'Ex.: Centro',
            'cidade': 'Ex.: Taiobeiras',
            'uf': 'Ex.: MG',
            'cep': 'Ex.: 00000-000',
            'phone': 'Ex.: (38) 99999-9999',
            'email': 'Ex.: contato@example.com',
            'insc_municipal': 'Informe a inscrição municipal',
            'latitude': 'Ex.: -15.8070',
            'longitude': 'Ex.: -42.2330',
            'cnae_principal': 'Ex.: 4712-1/00',
            'cnae_secundaria': 'Ex.: 4721-1/02',
            'classe': 'Ex.: SUPERMERCADO',
            'nome': 'Informe o nome completo',
            'cpf': 'Ex.: 000.000.000-00',
            'rg': 'Informe o número do RG',
            'nacionalidade': 'Ex.: Brasileira',
            'naturalidade': 'Ex.: Taiobeiras/MG',
            'estado_civil': 'Ex.: Solteiro(a)',
            'profissao': 'Ex.: Comerciante',
            'rg_conselho': 'Ex.: CRF-MG 00000',
        }
        self.fields['risco'].choices = [('', 'Selecione o grau de risco')] + [
            (valor, rotulo) for valor, rotulo in self.fields['risco'].choices if valor != ''
        ]
        for nome, campo in self.fields.items():
            nome_base = nome.removeprefix('resp_').removeprefix('rt_')
            campo.label = labels.get(nome_base, campo.label)
            campo.widget.attrs['class'] = 'form-control'
            if not isinstance(campo.widget, forms.Select):
                campo.widget.attrs['placeholder'] = placeholders[nome_base]

    @property
    def sections(self):
        grupos = (
            ('Dados do Estabelecimento', self.Meta.fields),
            ('Classificação', self.campos_tipo),
            ('Responsável pelo Estabelecimento', tuple(f'resp_{nome}' for nome in self.campos_responsavel)),
            ('Responsável Técnico (opcional)', tuple(f'rt_{nome}' for nome in self.campos_rt)),
            ('Fiscal responsável', ('fiscal_responsavel',)),
        )
        return [(titulo, [self[nome] for nome in campos]) for titulo, campos in grupos]

    def clean(self):
        dados = super().clean()
        # A view só cria um responsável se a seção tiver sido preenchida.
        if any(dados.get(f'resp_{nome}') for nome in self.campos_responsavel):
            for nome in self.campos_responsavel:
                if not Responsavel._meta.get_field(nome).blank and not dados.get(f'resp_{nome}'):
                    self.add_error(f'resp_{nome}', 'Este campo é obrigatório ao cadastrar o responsável.')

        for nome in ('uf', 'resp_uf', 'rt_uf'):
            valor = dados.get(nome)
            if valor:
                dados[nome] = valor.upper()
        for nome, limite in (('latitude', 90), ('longitude', 180)):
            valor = dados.get(nome)
            if valor is not None and not -limite <= valor <= limite:
                self.add_error(nome, f'Informe um valor entre -{limite} e {limite}.')
        return dados

    def dados_para_cadastro(self):
        """Converte os valores validados para os nomes já utilizados pela view."""
        dados = {}
        for nome, valor in self.cleaned_data.items():
            if nome == 'fiscal_responsavel':
                valor = valor.pk
            elif hasattr(valor, 'isoformat'):
                valor = valor.isoformat()
            dados[self.add_prefix(nome)] = '' if valor is None else str(valor)
        return dados


class AnaliseEstabelecimentoForm(EstabelecimentoForm):
    ativo = forms.ChoiceField(
        label='Status do cadastro', choices=(('1', 'Ativo'), ('0', 'Inativo')),
    )

    @property
    def analysis_sections(self):
        ordem = (
            'Dados do Estabelecimento', 'Responsável pelo Estabelecimento',
            'Responsável Técnico (opcional)', 'Classificação', 'Fiscal responsável',
        )
        secoes = dict(self.sections)
        return [
            {'titulo': titulo, 'campos': campos,
             'aberto': titulo in ('Classificação', 'Fiscal responsável') or any(campo.errors for campo in campos)}
            for titulo in ordem
            for campos in (secoes[titulo],)
        ]


class InspecaoForm(forms.ModelForm):
    """Inspeção e ações vinculadas ao registro de vigilância."""
    acoes = (
        ('Plano de trabalho', 'plano_aplicado', 'plano_status'),
        ('Termo de ciência', 'termo_ciencia', 'termo_status'),
        ('Interdição', 'interdicao', 'interdicao_status'),
        ('Processo', 'processo', 'processo_status'),
    )

    class Meta:
        model = Vigilancia
        fields = (
            'inspecao_status', 'ano_previsto', 'mes_previsto', 'data_realizacao', 'data_alvara', 'obs',
            'plano_aplicado', 'plano_status', 'termo_ciencia', 'termo_status',
            'interdicao', 'interdicao_status', 'processo', 'processo_status',
        )
        labels = {
            'ano_previsto': 'Ano previsto', 'mes_previsto': 'Mês previsto',
            'data_realizacao': 'Data de realização', 'obs': 'Observações',
        }
        widgets = {
            'data_realizacao': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'data_alvara': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'obs': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Observações sobre a inspeção'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_realizacao'].widget.attrs['max'] = timezone.localdate().isoformat()
        for name in ('data_realizacao', 'data_alvara'):
            self.fields[name].input_formats = ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y')
        self.fields['mes_previsto'].widget.attrs.update({'min': 1, 'max': 12, 'placeholder': 'De 1 a 12'})
        self.fields['ano_previsto'].widget.attrs.update({'min': 1, 'max': 9999, 'placeholder': 'Ex.: 2026'})
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        for titulo, acao, status in self.acoes:
            self.fields[acao].label = titulo
            self.fields[status].label = f'Status — {titulo.lower()}'
            self.fields[acao].widget.attrs['data-status-target'] = self[status].id_for_label
            self.fields[status].help_text = 'Obrigatório quando a ação estiver aplicada.'

    @property
    def sections(self):
        return [('Inspeção', [self[nome] for nome in self.Meta.fields])]

    def clean(self):
        data = super().clean()
        realizada = data.get('data_realizacao')
        if realizada:
            if realizada > timezone.localdate():
                self.add_error('data_realizacao', 'A data de realização não pode ser futura.')
            data['inspecao_status'] = Vigilancia.Status.CONCLUIDO
        elif data.get('inspecao_status') == Vigilancia.Status.CONCLUIDO:
            self.add_error('data_realizacao', 'Informe a data da inspeção concluída.')
        ano = data.get('ano_previsto')
        if ano is not None and not 1 <= ano <= 9999:
            self.add_error('ano_previsto', 'Informe um ano entre 1 e 9999.')
        for titulo, acao, status in self.acoes:
            if data.get(acao) == Vigilancia.Relatado.NAO_REQUERIDO:
                data[status] = None
            elif data.get(acao) == Vigilancia.Relatado.APLICADO and not data.get(status):
                self.add_error(status, f'Informe o status de {titulo.lower()}.')
        return data
