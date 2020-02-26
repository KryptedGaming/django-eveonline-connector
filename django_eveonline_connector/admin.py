from django.contrib import admin, messages
from django.conf import settings 
from django.apps import apps 
from django import forms
from django_eveonline_connector.models import EveClient, EveScope, EveCharacter, EveToken, EveCorporation, EveAlliance, EveTokenType

if settings.DEBUG:
    admin.site.register(EveCharacter)
    admin.site.register(EveToken)

app_config = apps.get_app_config('django_eveonline_connector')
if app_config.ESI_SECRET_KEY and app_config.ESI_CLIENT_ID and app_config.ESI_CALLBACK_URL and app_config.ESI_BASE_URL:
    pass 
else:
    if apps.is_installed('django_singleton_admin'):
        # Highly Recommended: https://github.com/porowns/django-singleton-admin
        from django_singleton_admin.admin import DjangoSingletonModelAdmin
        @admin.register(EveClient) 
        class EveClientAdmin(DjangoSingletonModelAdmin):
            fieldsets = (
                ('General Settings', {
                    'fields': ('esi_callback_url', 'esi_client_id', 'esi_secret_key', )
                }),
                ('Advanced Settings', {
                    'classes': ('collapse', 'open'),
                    'fields': ('esi_base_url',)
                }),
            )
    else:
        admin.site.register(EveClient)

admin.site.register(EveScope)
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