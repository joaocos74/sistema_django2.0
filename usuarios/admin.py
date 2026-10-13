from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from .models import PerfilUsuario


class PerfilInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    extra = 1
    max_num = 1


admin.site.unregister(get_user_model())


@admin.register(get_user_model())
class UsuarioAdmin(UserAdmin):
    inlines = (PerfilInline,)
