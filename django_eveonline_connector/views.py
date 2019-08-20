from django.shortcuts import render, redirect
from django_eveonline_connector.models import EveClient, EveToken, EveCharacter
from django.contrib import messages


def sso_callback(request):
    code = request.GET.get('code', None)
    eve_client = EveClient.get_eve_client()

    # verify token
    esi_security = EveClient.get_esi_security()
    esi_token = esi_security.auth(code)
    esi_character = esi_security.verify()

    # create character
    character = EveCharacter.objects.get_or_create(
        external_id=esi_character['sub'].split(":")[-1],
        name=esi_character['name'],
    )[0]

    # create token
    token = EveToken.objects.get_or_create(character=character)[0]
    token.access_token = esi_token['access_token']
    token.refresh_token = esi_token['refresh_token']
    token.expires_in = esi_token['expires_in']
    token.scopes.set(eve_client.esi_scopes.all())
    token.user = request.user
    token.save()

    return redirect('app-dashboard')  # TODO: Redirect to EVE Character view


def add_sso_token(request):
    return redirect(EveClient.get_eve_client().esi_sso_url)


def remove_sso_token(request, pk):
    eve_token = EveToken.objects.get(pk=pk)
    if request.user == eve_token.user:
        eve_token.delete()
    else:
        messages.error(request, "You cannot delete someone elses token.")
    pass
