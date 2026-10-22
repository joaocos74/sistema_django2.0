from django import forms
from .models import ItemAgenda, Lembrete


class LembreteForm(forms.ModelForm):
    class Meta:
        model = Lembrete
        fields = ('texto',)
        widgets = {'texto': forms.TextInput(attrs={
            'placeholder': 'Novo lembrete', 'autocomplete': 'off',
            'aria-label': 'Novo lembrete',
        })}


class ItemAgendaForm(forms.ModelForm):
    class Meta:
        model = ItemAgenda
        fields = ('dia', 'turno', 'texto', 'feito')
