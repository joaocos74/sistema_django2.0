from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction
from .models import PerfilUsuario, PALETA_CORES


class CorAgendaMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cor'] = forms.RegexField(
            regex=r'^#[0-9a-fA-F]{6}$', label='Cor da agenda',
            initial='#fef08a', widget=forms.TextInput(attrs={'type': 'color'}),
            help_text='Cor dos lembretes criados por este usuário.',
        )
        if self.instance.pk:
            perfil = getattr(self.instance, 'perfil', None)
            self.fields['cor'].initial = perfil.cor if perfil else PALETA_CORES[(self.instance.pk - 1) % len(PALETA_CORES)]

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            PerfilUsuario.objects.update_or_create(user=user, defaults={'cor': self.cleaned_data['cor']})
        return user



class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update(
            placeholder='Digite seu usuário', autocomplete='username',
        )
        self.fields['password'].widget.attrs.update(
            placeholder='Digite sua senha', autocomplete='current-password',
        )


class PerfilForm(CorAgendaMixin, forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'email')
        labels = {'first_name': 'Nome', 'last_name': 'Sobrenome', 'email': 'E-mail'}
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Seu nome', 'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Seu sobrenome', 'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'seu@email.com', 'autocomplete': 'email'}),
        }


class CadastroUsuarioForm(CorAgendaMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username',)
        labels = {'first_name': 'Nome', 'last_name': 'Sobrenome', 'email': 'E-mail'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['placeholder'] = field.label
        self.fields['username'].widget.attrs['autocomplete'] = 'username'
        for name in ('password1', 'password2'):
            self.fields[name].widget.attrs['autocomplete'] = 'new-password'
