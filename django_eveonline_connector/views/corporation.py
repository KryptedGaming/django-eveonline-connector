from django.shortcuts import render, redirect
from django_eveonline_connector.models import EveCorporation, EveCharacter, PrimaryEveCharacterAssociation, EveStructure
from django.contrib import messages
from django.db.models import Q 
from itertools import chain
from django.contrib.auth.decorators import login_required, permission_required

import logging
logger = logging.getLogger(__name__)

@login_required
@permission_required('django_eveonline_connector.view_evecorporation', raise_exception=True)
def view_corporations(request):
    return render(request, 'django_eveonline_connector/adminlte/corporations/list_corporations.html', context={
        'corporations': EveCorporation.objects.filter(track_corporation=True)
    })


@login_required
@permission_required('django_eveonline_connector.view_evecorporation', raise_exception=True)
def view_corporation(request, external_id):
    context = {}
    context['corporation'] = EveCorporation.objects.get(external_id=external_id)
    context['characters'] = PrimaryEveCharacterAssociation.objects.filter(
        character__corporation=context['corporation'])
    context['unauthorized_characters'] = list(
        chain(
            EveCharacter.objects.filter(corporation=context['corporation'], token=None),
            EveCharacter.objects.filter(corporation=context['corporation']).exclude(Q(token__invalidated=None))
        )
    )
    return render(request, 'django_eveonline_connector/adminlte/corporations/view_corporation_roster.html', context)


@login_required
@permission_required('django_eveonline_connector.view_evecorporation', raise_exception=True)
def view_corporation_structures(request, external_id):
    if request.user.primary_evecharacter.character.corporation.external_id == external_id and not request.user.has_perm('django_eveonline_connector.bypass_corporation_view_requirements'):
        messages.error(request, "You do not have permission to view those structures, as you are not a member of that corporation or are missing the BYPASS permission")
        return redirect('django-eveonline-connector-view-corporation', external_id)
    context = {
        'corporation': EveCorporation.objects.get(external_id=external_id),
        'structures': EveStructure.objects.filter(entity__external_id=external_id)
    }
    return render(request, 'django_eveonline_connector/adminlte/corporations/view_corporation_structures.html', context)

