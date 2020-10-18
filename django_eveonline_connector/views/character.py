from django.http import HttpResponse
from django.shortcuts import render, redirect
from django_eveonline_connector.models import EveCharacter, EveSkill, PrimaryEveCharacterAssociation
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django_eveonline_connector.tasks import *

import logging
logger = logging.getLogger(__name__)


@login_required
def set_primary_character(request, character_id):
    character = EveCharacter.objects.get(external_id=character_id)
    if not character.token:
        messages.warning(request, "You may not set a primary character that does not have a token.")
        return redirect("/")
    elif not character.token.user == request.user:
        messages.warning(request, "You may not set a primary character that you do not own.")
        return redirect("/")
    
    if PrimaryEveCharacterAssociation.objects.filter(user=request.user).exists():
        assoc = PrimaryEveCharacterAssociation.objects.get(user=request.user)
        assoc.character = character 
        assoc.save()
    else:
        PrimaryEveCharacterAssociation.objects.create(
            user=request.user,
            character=character
        )

    messages.success(request, "Successfully updated primary character to %s" % character)
    return redirect("/")


@login_required
def select_primary_character(request):
    return render(request, 'django_eveonline_connector/adminlte/select_primary_character.html', context={
        'characters': EveCharacter.objects.filter(token__user=request.user),
    })

@login_required
def select_character(request, required_scopes, next):
    return redirect(next, character_id)

@login_required
def refresh_character_public(request, external_id):
    character = EveCharacter.objects.get(external_id=external_id)
    character.token.refresh()
    character.update_character_corporation()
    messages.success(request, "Character successfully updated")
    return redirect("/")

@login_required
@permission_required('django_eveonline_connector.change_evecharacter')
def refresh_character(request, external_id):
    if 'fields' not in request.GET:
       return HttpResponse(status=400)
    scopes = request.GET['fields'].split(",")
    
    if 'assets' in scopes:
        update_character_assets.apply_async(args=[external_id])
    if 'jumpclones' in scopes:
        update_character_jumpclones.apply_async(args=[external_id])
    if 'contacts' in scopes:
        update_character_contacts.apply_async(args=[external_id])
    if 'contracts' in scopes:
        update_character_contracts.apply_async(args=[external_id])
    if 'skills' in scopes:
        update_character_skills.apply_async(args=[external_id])
    if 'journal' in scopes:
        update_character_journal.apply_async(args=[external_id])
    if 'transactions' in scopes:
        update_character_transactions.apply_async(args=[external_id])
        
    messages.info(request, f"Jobs queued to update: {scopes}")
    return redirect('django-eveonline-connector-view-character', external_id)

@login_required
@permission_required('django_eveonline_connector.view_evecharacter', raise_exception=True)
def list_characters(request):
    return render(request, 'django_eveonline_connector/adminlte/characters/list_characters.html', context={
        'characters': EveCharacter.objects.all()
    })


@login_required
@permission_required('django_eveonline_connector.view_evecharacter', raise_exception=True)
def view_character(request, external_id):
    context = {}
    context['character'] = EveCharacter.objects.get(external_id=external_id)
    context['message'] = "A String"
    return render(request, 'django_eveonline_connector/adminlte/characters/view_character.html', context)


@login_required
@permission_required('django_eveonline_connector.view_evecharacter', raise_exception=True)
@permission_required('django_eveonline_connector.view_eveasset', raise_exception=True)
def view_character_assets(request, external_id):
    character = EveCharacter.objects.get(external_id=external_id)
    return render(
        request,
        'django_eveonline_connector/adminlte/characters/view_character_assets.html',
        context={
            'character': character,
        }
    )


@login_required
@permission_required('django_eveonline_connector.view_evecharacter', raise_exception=True)
@permission_required('django_eveonline_connector.view_evejumpclone', raise_exception=True)
def view_character_clones(request, external_id):
    character = EveCharacter.objects.get(external_id=external_id)
    return render(
        request,
        'django_eveonline_connector/adminlte/characters/view_character_clones.html',
        context={
            'character': character,
        }
    )


@login_required
@permission_required('django_eveonline_connector.view_evecharacter', raise_exception=True)
@permission_required('django_eveonline_connector.view_evecontract', raise_exception=True)
def view_character_contracts(request, external_id):
    character = EveCharacter.objects.get(external_id=external_id)
    return render(
        request,
        'django_eveonline_connector/adminlte/characters/view_character_contracts.html',
        context={
            'character': character,
        }
    )


@login_required
@permission_required('django_eveonline_connector.view_evecharacter', raise_exception=True)
@permission_required('django_eveonline_connector.view_evecontact', raise_exception=True)
def view_character_contacts(request, external_id):
    character = EveCharacter.objects.get(external_id=external_id)
    return render(
        request,
        'django_eveonline_connector/adminlte/characters/view_character_contacts.html',
        context={
            'character': character,
        }
    )


@login_required
@permission_required('django_eveonline_connector.view_evecharacter', raise_exception=True)
@permission_required('django_eveonline_connector.view_eveskill', raise_exception=True)
def view_character_skills(request, external_id):
    character = EveCharacter.objects.get(external_id=external_id)
    character_skills = EveSkill.objects.filter(entity=character)
    return render(
        request,
        'django_eveonline_connector/adminlte/characters/view_character_skills.html',
        context={
            'character': character,
            'skills': character_skills,
            'skill_names': ",".join([skill.skill_name for skill in character_skills]),
            'skill_levels': ",".join([str(skill.trained_skill_level) for skill in character_skills]),
            'groups': set([skill.skill_group for skill in character_skills]),
        }
    )


@login_required
@permission_required('django_eveonline_connector.view_evecharacter', raise_exception=True)
@permission_required('django_eveonline_connector.view_evejournalentry', raise_exception=True)
def view_character_journal(request, external_id):
    character = EveCharacter.objects.get(external_id=external_id)
    return render(
        request,
        'django_eveonline_connector/adminlte/characters/view_character_journal.html',
        context={
            'character': character,
        }
    )


@login_required
@permission_required('django_eveonline_connector.view_evecharacter', raise_exception=True)
@permission_required('django_eveonline_connector.view_evetransaction', raise_exception=True)
def view_character_transactions(request, external_id):
    character = EveCharacter.objects.get(external_id=external_id)
    return render(
        request,
        'django_eveonline_connector/adminlte/characters/view_character_transactions.html',
        context={
            'character': character,
        }
    )


@login_required
@permission_required('django_eveonline_connector.view_evecharacter', raise_exception=True)
def view_character_audit(request, external_id):
    character = EveCharacter.objects.get(external_id=external_id)
    return render(
        request,
        'django_eveonline_connector/adminlte/characters/view_character_audit.html',
        context={
            'character': character,
        }
    )
