from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path
from django_eveonline_connector.views import sso, character, corporation, api

# SSO 
urlpatterns = [
    path('sso/callback', sso.sso_callback,
         name="django-eveonline-connector-sso-callback"),
    path('sso/token/add/', sso.add_sso_token,
         name="django-eveonline-connector-sso-token-add"),
    path('sso/token/update/<int:token_id>/', sso.update_sso_token,
         name="django-eveonline-connector-sso-token-update"),
    path('sso/token/remove/<int:pk>/', sso.remove_sso_token,
         name="django-eveonline-connector-sso-token-remove"),

]

# Characters
urlpatterns += [
    path('characters/', character.list_characters,
         name="django-eveonline-connector-characters-view"),
    path('characters/select-primary/', character.select_primary_character,
         name="django-eveonline-connector-character-select-primary"),
    path('characters/select-character/', character.select_character,
         name="django-eveonline-connector-character-select"),
    path('character/<int:character_id>/set-primary/', character.set_primary_character,
         name="django-eveonline-connector-character-set-primary"),
    path('character/<int:external_id>/refresh/', character.refresh_character_public,
         name='django-eveonline-connector-character-refresh-public'),
    path('character/view/<int:external_id>/', character.view_character,
         name="django-eveonline-connector-view-character"),
    path('character/refresh/<int:external_id>/', character.refresh_character,
         name="django-eveonline-connector-refresh-character"),
    path('character/view/<int:external_id>/assets/', character.view_character_assets,
         name="django-eveonline-connector-view-character-assets"),
    path('character/view/<int:external_id>/clones/', character.view_character_clones,
         name="django-eveonline-connector-view-character-clones"),
    path('character/view/<int:external_id>/contacts/', character.view_character_contacts,
         name="django-eveonline-connector-view-character-contacts"),
    path('character/view/<int:external_id>/contracts/', character.view_character_contracts,
         name="django-eveonline-connector-view-character-contracts"),
    path('character/view/<int:external_id>/skills/', character.view_character_skills,
         name="django-eveonline-connector-view-character-skills"),
    path('character/view/<int:external_id>/journal/', character.view_character_journal,
         name="django-eveonline-connector-view-character-journal"),
    path('character/view/<int:external_id>/transactions/', character.view_character_transactions,
         name="django-eveonline-connector-view-character-transactions"),
    path('character/view/<int:external_id>/audit/', character.view_character_audit,
         name="django-eveonline-connector-view-character-audit"),
]

# Corporation 
urlpatterns += [
    path('corporations/', corporation.view_corporations,
         name="django-eveonline-connector-corporations-view"),
         path('corporation/refresh/<int:external_id>/', corporation.refresh_corporation,
         name="django-eveonline-connector-refresh-corporation"),
    path('corporation/view/<int:external_id>/', corporation.view_corporation,
         name="django-eveonline-connector-view-corporation"),
    path('corporation/view/<int:external_id>/structures/', corporation.view_corporation_structures,
         name="django-eveonline-connector-view-corporation-structures"),
    # path('corporation/refresh/<int:external_id>/', character.refresh_corporation,
    #      name="django-eveonline-connector-refresh-corporation"),
]

# Alliance
# urlpatterns += [
#     path('alliance/view/<int:external_id>/', character.view_alliance,
#          name="django-eveonline-connector-view-alliance"),
# ]

# Utilities
urlpatterns += [
    path('api/entity/resolve', api.get_entity_info,
        name="django-eveonline-connector-api-get-entity-info"),
]

# JSON
urlpatterns += [
    path('api/characters/', api.get_characters,
         name="django-eveonline-connector-api-characters"),
    path('api/assets/', api.get_assets,
         name="django-eveonline-connector-api-assets"),
    path('api/clones/', api.get_clones,
         name="django-eveonline-connector-api-clones"),
    path('api/contacts/', api.get_contacts,
         name="django-eveonline-connector-api-contacts"),
    path('api/contracts/', api.get_contracts,
         name="django-eveonline-connector-api-contracts"),
    path('api/journal/', api.get_journal,
         name="django-eveonline-connector-api-journal"),
    path('api/transactions/', api.get_transactions,
         name="django-eveonline-connector-api-transactions"),
]
