from django.contrib import admin
from django_eveonline_connector.models import EveClient, EveScope, EveCharacter, EveToken, EveCorporation, EveAlliance

admin.site.register(EveClient)
admin.site.register(EveScope)
