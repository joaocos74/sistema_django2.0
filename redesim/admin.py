from django.contrib import admin
from .models import RegistroRedesim


@admin.register(RegistroRedesim)
class RegistroRedesimAdmin(admin.ModelAdmin):
    list_display = ('id', 'estabelecimento', 'data_liberacao', 'fiscal', 'criado_em')
    search_fields = ('cnpj_cpf', 'razao_social')

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
