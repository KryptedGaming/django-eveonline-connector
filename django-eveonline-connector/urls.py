from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('sso/callback', views.sso_callback,
         name="django-eveonline-connector-sso-callback"),
    path('sso/token/add/', views.add_sso_token,
         name="django-eveonline-connector-sso-token-add"),
    path('sso/token/remove/<int:pk>/', views.remove_sso_token,
         name="django-eveonline-connector-sso-token-remove"),
]
