from django.shortcuts import render, redirect
from django_eveonline_connector.models import EveClient, EveToken, EveCharacter, EveScope, EveCorporation
from django.contrib import messages
from django_eveonline_connector.tasks import update_character_corporation

import logging
logger = logging.getLogger(__name__)

"""
SSO Views
"""
def sso_callback(request):
    code = request.GET.get('code', None)
    eve_client = EveClient.get_instance()

    # verify token
    esi_security = EveClient.get_esi_security()
    esi_token = esi_security.auth(code)
    esi_character = esi_security.verify()

    # create new token 
    new_token = EveToken.objects.get_or_create(
        access_token = esi_token['access_token'], 
        refresh_token = esi_token['refresh_token'],
        expires_in = esi_token['expires_in'],
        user=request.user
    )[0]

    # set scopes M2M
    new_token.scopes.set(EveScope.objects.all())

    # find or create character
    if EveCharacter.objects.filter(external_id=esi_character['sub'].split(":")[-1]).exists():
        character = EveCharacter.objects.get(external_id=esi_character['sub'].split(":")[-1])
        if character.token:
            old_token = character.token 
            old_token.delete()
        character.token = new_token 
        character.save()
    else:
        character = EveCharacter.objects.create(
            external_id=esi_character['sub'].split(":")[-1],
            name=esi_character['name'],
            token=new_token,
        )

    # if no primary token, set as primary token
    if not EveToken.objects.filter(user=request.user, primary=True).exists():
        logger.info("Setting primary token as %s for %s" % (esi_character['name'], request.user))
        new_token.primary = True 
        new_token.save()

    return redirect('app-dashboard')  # TODO: Redirect to EVE Character view


def add_sso_token(request):
    return redirect(EveClient.get_instance().esi_sso_url)


def remove_sso_token(request, pk):
    eve_token = EveToken.objects.get(pk=pk)
    if request.user == eve_token.user:
        eve_token.delete()
        messages.success(request, "Successfully deleted EVE Online character")
    else:
        messages.error(request, "You cannot delete someone elses token.")
    return redirect("/")

def refresh_character(request, external_id):
    update_character_corporation(external_id)
    messages.success(request, "Character successfully updated")
    return redirect("/")

def view_characters(request):
    return render(request, 'django_eveonline_connector/adminlte/view_characters.html',context = {
        'characters': EveCharacter.objects.all()
    })

def view_corporations(request):
    return render(request, 'django_eveonline_connector/adminlte/view_corporations.html',context = {
        'corporations': EveCharacter.objects.all()
    })