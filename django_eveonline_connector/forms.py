from django import forms
from django.forms import ModelForm
from .models import EveClient

class EveClientForm(ModelForm):
    esi_callback_url = forms.URLField(label="ESI Callback URL")
    esi_client_id = forms.CharField(max_length=255, label="ESI Client ID")
    esi_secret_key = forms.CharField(max_length=255, label="ESI Secret Key")

    class Meta:
        model = EveClient
        fields = ['esi_callback_url', 'esi_client_id', 'esi_secret_key']
