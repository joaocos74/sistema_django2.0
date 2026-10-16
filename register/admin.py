from django.contrib import admin

from .models import (
    Documento,
    Estabelecimento,
    Responsavel,
    RTResponsavel,
    Tipo,
    Vigilancia,
    HistoricoPasta,
)


class RegistroAdmin(admin.ModelAdmin):
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 50


@admin.register(Estabelecimento)
class EstabelecimentoAdmin(RegistroAdmin):
    list_display = ("numero_pasta", "nome_fantasia", "cnpj", "razao_social", "bairro", "cidade", "status",)
    search_fields = ("=numero_pasta", "nome_fantasia", "cnpj", "razao_social", "logradouro", "bairro",)
    list_filter = ("status", "uf", "cidade")
    ordering = ("numero_pasta", "id")

    def get_readonly_fields(self, request, obj=None):
        campos = super().get_readonly_fields(request, obj)
        return campos if request.user.is_superuser else campos + ('numero_pasta',)

    def save_model(self, request, obj, form, change):
        obj.save(usuario=request.user)


@admin.register(HistoricoPasta)
class HistoricoPastaAdmin(admin.ModelAdmin):
    list_display = ('estabelecimento', 'numero_anterior', 'numero_novo', 'inativo_novo', 'alterado_por', 'criado_em')
    list_select_related = ('estabelecimento', 'alterado_por')
    search_fields = ('=numero_anterior', '=numero_novo', 'estabelecimento__nome_fantasia')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Tipo)
class TipoAdmin(RegistroAdmin):
    readonly_fields = RegistroAdmin.readonly_fields + ("alterado_por",)

    def save_model(self, request, obj, form, change):
        if not change or form.changed_data:
            vigilancia = obj.estabelecimento.fiscalizacoes.order_by('-id').first()
            obj.alterado_por = vigilancia.fiscal if vigilancia else None
        super().save_model(request, obj, form, change)

    list_display = ("id", "estabelecimento", "risco", "cnae_principal", "classe", "created_at")
    search_fields = ("estabelecimento__nome_fantasia", "estabelecimento__cnpj", "cnae_principal", "cnae_secundaria", "classe",)
    list_filter = ("risco", "classe")
    autocomplete_fields = ("estabelecimento",)
    list_select_related = ("estabelecimento",)
    ordering = ("-created_at", "-id")


@admin.register(Responsavel)
class ResponsavelAdmin(RegistroAdmin):
    list_display = ("id", "nome", "estabelecimento", "cpf", "phone")
    search_fields = ("nome", "cpf", "estabelecimento__nome_fantasia", "estabelecimento__cnpj")
    autocomplete_fields = ("estabelecimento",)
    list_select_related = ("estabelecimento",)
    ordering = ("nome", "id")


@admin.register(RTResponsavel)
class RTResponsavelAdmin(ResponsavelAdmin):
    list_display = ("id", "nome", "estabelecimento", "profissao", "rg_conselho", "phone")
    search_fields = ResponsavelAdmin.search_fields + ("rg_conselho",)
    list_filter = ("profissao",)


@admin.register(Vigilancia)
class VigilanciaAdmin(RegistroAdmin):
    list_display = ("id", "estabelecimento", "fiscal", "inspecao_status","ano_previsto", "mes_previsto", "data_realizacao",)
    search_fields = ("=id", "estabelecimento__nome_fantasia", "estabelecimento__cnpj", "fiscal__username", "fiscal__first_name", "fiscal__last_name", "obs",)
    list_filter = ("inspecao_status", "fiscal", "ano_previsto", "mes_previsto")
    autocomplete_fields = ("estabelecimento", "fiscal")
    list_select_related = ("estabelecimento", "fiscal")
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-id")


@admin.register(Documento)
class DocumentoAdmin(RegistroAdmin):
    list_display = ("id", "nome", "estabelecimento", "tipo_documento", "enviado_por", "data_envio")
    search_fields = ("nome", "estabelecimento__nome_fantasia", "estabelecimento__cnpj", "enviado_por__username",)
    list_filter = ("tipo_documento", "data_envio")
    autocomplete_fields = ("estabelecimento",)
    list_select_related = ("estabelecimento", "enviado_por")
    readonly_fields = RegistroAdmin.readonly_fields + ("data_envio", "enviado_por")
    date_hierarchy = "data_envio"
    ordering = ("-data_envio", "-id")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.enviado_por = request.user
        super().save_model(request, obj, form, change)
