from django.contrib import admin
from .models import ItemAgenda


@admin.register(ItemAgenda)
class ItemAgendaAdmin(admin.ModelAdmin):
    list_display = ('dia', 'turno', 'autor', 'feito')
    list_filter = ('turno', 'feito', 'dia')
    search_fields = ('texto', 'autor__username')
    autocomplete_fields = ('autor', 'mencionados')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset if request.user.is_superuser else queryset.filter(autor=request.user)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (obj is None or request.user.is_superuser or obj.autor_id == request.user.pk)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and (obj is None or request.user.is_superuser or obj.autor_id == request.user.pk)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.autor = request.user
        super().save_model(request, obj, form, change)
