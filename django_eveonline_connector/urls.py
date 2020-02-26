from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('sso/callback', views.sso_callback,
         name="django-eveonline-connector-sso-callback"),
    path('sso/token/type/select/', views.select_sso_token_type,
         name="django-eveonline-connector-sso-token-type-select"),
    path('sso/token/add/<str:token_type_name>/', views.add_sso_token,
         name="django-eveonline-connector-sso-token-add"),
    path('sso/token/remove/<int:pk>/', views.remove_sso_token,
         name="django-eveonline-connector-sso-token-remove"),
    path('character/<int:external_id>/set-primary/', views.set_primary_character,
         name="django-eveonline-connector-character-set-primary"),
    path('character/<int:external_id>/refresh/', views.refresh_character,
         name='django-eveonline-connector-character-refresh'),
    path('characters/', views.view_characters,
         name="django-eveonline-connector-characters-view"),
    path('corporations/', views.view_corporations,
         name="django-eveonline-connector-corporations-view"),
]
