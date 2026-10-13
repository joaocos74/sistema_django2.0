from django.contrib import admin
from .models import Denuncia


@admin.register(Denuncia)
class DenunciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'razao_social', 'estabelecimento', 'data_denuncia', 'status', 'fiscal_responsavel')
    list_filter = ('status', 'tipo')
    search_fields = ('cnpj', 'razao_social', 'nome_fantasia')

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
