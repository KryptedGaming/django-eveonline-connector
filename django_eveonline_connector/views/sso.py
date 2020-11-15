from django.shortcuts import render, redirect
from django_eveonline_connector.models import EveClient, EveToken, EveCharacter, EveScope, EveCorporation, PrimaryEveCharacterAssociation
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django_eveonline_connector.tasks import update_character

import logging
logger = logging.getLogger(__name__)

"""
SSO Views
"""
@login_required
def sso_callback(request):
    code = request.GET.get('code', None)
    eve_client = EveClient.get_instance()

    # verify token
    esi_security = EveClient.get_esi_security()
    esi_token = esi_security.auth(code)
    esi_character = esi_security.verify()

    # create new token
    new_token = EveToken.objects.get_or_create(
        access_token=esi_token['access_token'],
        refresh_token=esi_token['refresh_token'],
        expires_in=esi_token['expires_in'],
        user=request.user
    )[0]

    # set scopes M2M
    scopes = EveScope.objects.filter(name__in=esi_character['scp'])
    if scopes.count() != len(esi_character['scp']):
        logger.error(
            f"Whoa there. Somehow we added a scope we don't know about. Pass this to Krypted Developers: \n ${esi_character['scp']}")
    new_token.scopes.set(scopes)

    # find or create character
    if EveCharacter.objects.filter(external_id=esi_character['sub'].split(":")[-1]).exists():
        character = EveCharacter.objects.get(
            external_id=esi_character['sub'].split(":")[-1])
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

    # if no primary user, set 
    if not PrimaryEveCharacterAssociation(user=request.user):
        PrimaryEveCharacterAssociation.objects.create(
            user=request.user,
            character=character
        )

    update_character.apply_async(args=[character.external_id])

    return redirect('app-dashboard')  # TODO: Redirect to EVE Character view

@login_required
def add_sso_token(request):
    return redirect(EveClient.get_instance().get_sso_url())

@login_required
def update_sso_token(request, token_id):
    eve_token = EveToken.objects.get(pk=token_id)
    return redirect(EveClient.get_instance().get_sso_url(
        EveScope.convert_to_list(eve_token.requested_scopes.all())
        ))

@login_required
def remove_sso_token(request, pk):
    eve_token = EveToken.objects.get(pk=pk)
    if request.user == eve_token.user:
        eve_token.delete()
        messages.success(request, "Successfully deleted EVE Online character")
    else:
        messages.error(request, "You cannot delete someone elses token.")
    return redirect("/")
