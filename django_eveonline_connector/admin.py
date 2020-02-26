from django.contrib import admin, messages
from django_eveonline_connector.models import EveClient, EveScope, EveCharacter, EveToken, EveCorporation, EveAlliance, EveTokenType

admin.site.register(EveClient)
admin.site.register(EveScope)
admin.site.register(EveCharacter)
admin.site.register(EveToken)

@admin.register(EveTokenType)
class EveTokenTypeAdmin(admin.ModelAdmin):
    def delete_model(self, request, obj):
        try:
            obj.delete()
        except Exception as e: 
            messages.warning(request, "Default Token Type was generated. At least one instance must exist.")
    
    def delete_queryset(self, request, queryset):
        for obj in queryset:
            try:
                obj.delete()
            except Exception as e: 
                messages.warning(request, "Default Token Type was generated. At least one instance must exist.")