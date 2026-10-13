from django import forms
from .models import ItemAgenda


class ItemAgendaForm(forms.ModelForm):
    class Meta:
        model = ItemAgenda
        fields = ('dia', 'turno', 'texto', 'feito')
