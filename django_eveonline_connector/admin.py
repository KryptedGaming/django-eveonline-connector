from django.contrib import admin, messages
from django.conf import settings 
from django.apps import apps 
from django import forms
from django_eveonline_connector.models import EveClient, EveScope, EveCharacter, EveToken, EveCorporation, EveAlliance, EveStructure
from django.urls import reverse
from django.utils.safestring import mark_safe


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

@admin.register(EveScope)
class EveScopeAdmin(admin.ModelAdmin):
    list_display = ('name', 'required')

@admin.register(EveCorporation)
class EveCorporationAdmin(admin.ModelAdmin):
    list_display = ('name', 'ceo', 'track_corporation', 'track_characters')
    search_fields = ('name', 'ceo__name')

@admin.register(EveToken)
class EveTokenAdmin(admin.ModelAdmin):
    list_display = ('is_valid', 'evecharacter', 'user')
    search_fields = ('evecharacter__name',)

    def is_valid(self, obj):
        return obj.valid
    is_valid.boolean = True

@admin.register(EveCharacter)
class EveCharacterAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_corporation', 'get_user')
    search_fields = ('name', )

    @mark_safe
    def get_corporation(self, obj):
        if obj.corporation:
            link = reverse("admin:django_eveonline_connector_evecorporation_change", args=[
                           obj.corporation.pk])
            return u'<a href="%s">%s</a>' % (link, obj.corporation.name)
        else:
            return None 
    get_corporation.allow_tags=True
    get_corporation.short_description = "Corporation"

    @mark_safe 
    def get_user(self, obj):
        if obj.token: 
            link = reverse("admin:auth_user_change", args=[obj.token.user.pk])
            return u'<a href="%s">%s</a>' % (link, obj.token.user.username)
        else:
            return None 
    get_user.short_description = "User"

admin.site.register(EveStructure)