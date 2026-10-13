from django import forms
from django.utils import timezone


class LiberacaoForm(forms.Form):
    estabelecimento_id = forms.IntegerField(min_value=1)
    cnpj_ou_cpf = forms.CharField(max_length=18)
    alvara = forms.DateField(required=False)
    observacoes = forms.CharField(required=False, max_length=10000)

    def clean_alvara(self):
        data = self.cleaned_data['alvara']
        if data and data > timezone.localdate():
            raise forms.ValidationError('A data da liberação não pode ser futura.')
        return data
