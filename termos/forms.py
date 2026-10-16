from django import forms

class PadraoForm(forms.Form):
    campo_numero_pasta = 'campo_03'
    autoridades_extras = forms.JSONField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        nomes = [f'campo_{n:02d}' for n in range(1, 33)] + [
            'autoridade_nome', 'autoridade_nome_2', 'campo_38_funcao_1',
            'campo_38_funcao_2', 'campo_38_dia', 'campo_38_mes', 'campo_38_ano', 'campo_38_hora']
        for nome in nomes:
            if nome == self.campo_numero_pasta:
                continue
            self.fields[nome] = forms.CharField(required=False, max_length=2000, strip=False)

    def clean_autoridades_extras(self):
        valor = self.cleaned_data['autoridades_extras']
        if valor is None:
            return []
        if not isinstance(valor, list) or len(valor) > 20:
            raise forms.ValidationError('Informe no máximo 20 autoridades adicionais.')
        for item in valor:
            if not isinstance(item, dict) or set(item) != {'nome', 'funcao'} or any(
                not isinstance(v, str) or len(v) > 500 for v in item.values()
            ):
                raise forms.ValidationError('Autoridade inválida.')
        return valor

    campo_33 = forms.CharField(required=False, max_length=10000, strip=False)
    campo_34_tipo = forms.CharField(required=False, max_length=500, strip=False)
    campo_34_fato = forms.CharField(required=False, max_length=2000, strip=False)
    campo_36 = forms.CharField(required=False, max_length=10000, strip=False)
    campo_37 = forms.CharField(required=False, max_length=10000, strip=False)
    chk_auto = forms.BooleanField(required=False)
    chk_fato = forms.BooleanField(required=False)
    chk_termo = forms.BooleanField(required=False)
    chk_estab = forms.BooleanField(required=False)


class NotificacaoForm(PadraoForm):
    campo_numero_pasta = None
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome in ['campo_email'] + [
            f'{campo}_{n}' for n in (1, 2) for campo in (
                'campo_34_nome', 'campo_35_matricula', 'campo_36_cargo',
                'testemunha_nome', 'testemunha_rg', 'testemunha_endereco')
        ]:
            self.fields[nome] = forms.CharField(required=False, max_length=2000, strip=False)

    def clean_autoridades_extras(self):
        valor = self.cleaned_data['autoridades_extras']
        if valor is None:
            return []
        if not isinstance(valor, list) or len(valor) > 20:
            raise forms.ValidationError('Informe no máximo 20 autoridades adicionais.')
        for item in valor:
            if not isinstance(item, dict) or set(item) != {'nome', 'matricula', 'funcao'} or any(
                not isinstance(v, str) or len(v) > 500 for v in item.values()
            ):
                raise forms.ValidationError('Autoridade inválida.')
        return valor
