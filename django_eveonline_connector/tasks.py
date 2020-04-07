from celery import task, shared_task
from .models import *
from .services.esi.assets import get_eve_character_assets
from .services.esi.clones import get_eve_character_clones
from .services.esi.contacts import get_eve_character_contacts

import logging
logger = logging.getLogger(__name__)

"""
Global Tasks
These are what users register to maintain up-to-date EveEntity information.
"""
@shared_task
def update_affiliations():
    """
    Update the affiliations (character corporations, corporation alliances)
    Cached for 3600 seconds, so don't run it more frequently than that. 
    """
    character_ids = EveCharacter.objects.all().values_list('external_id', flat=True)
    affiliations = EveClient.call(
        'post_characters_affiliation', characters=character_ids).data

    for affiliation in affiliations:
        try:
            character = EveCharacter.objects.get(
                external_id=affiliation['character_id'])
            if not EveCorporation.objects.filter(external_id=affiliation['corporation_id']):
                EveCorporation.create_from_external_id(
                    affiliation['corporation_id'])
            corporation = EveCorporation.objects.get(
                external_id=affiliation['corporation_id'])
            if 'alliance_id' in affiliation:
                if not EveAlliance.objects.filter(external_id=affiliation['alliance_id']):
                    EveAlliance.create_from_external_id(affiliation['alliance_id'])
                alliance = EveAlliance.objects.get(external_id=affiliation['alliance_id'])
            else:
                alliance = None 

            character.corporation = corporation
            character.save()
            if alliance:
                corporation.alliance = alliance
                corporation.save()
        except Exception as e:
            logger.error("Failed to update affiliation: %s" % affiliation)
            logger.exception(e)
            
@shared_task
def update_all_characters():
    for eve_character in EveCharacter.objects.all():
        update_character_corporation.apply_async(
            args=[eve_character.external_id])


@shared_task
def update_all_corporations():
    for eve_corporation in EveCorporation.objects.all():
        update_corporation_alliance.apply_async(
            args=[eve_corporation.external_id])
        update_corporation_ceo.apply_async(
            args=[eve_corporation.external_id])


@shared_task
def update_all_alliances():
    for eve_alliance in EveAlliance.objects.all():
        update_alliance_executor.apply_async(args=[eve_alliance.external_id])


"""
EveCharacter Tasks
These tasks are used to keep EveCharacter attributes up to date.
"""

@shared_task
def update_character_corporation(character_id):
    esi_operation = EveClient.get_esi_app(
    ).op['get_characters_character_id'](character_id=character_id)
    response = EveClient.get_esi_client().request(esi_operation)

    corporation_id = response.data['corporation_id']
    eve_character = EveCharacter.objects.get(external_id=character_id)

    if EveCorporation.objects.filter(external_id=corporation_id).exists():
        eve_character.corporation = EveCorporation.objects.get(
            external_id=corporation_id)
    else:
        eve_character.corporation = EveCorporation.create_from_external_id(
            corporation_id)

    eve_character.save()

"""
EveCorporation Tasks
These tasks are used to keep EveCorporation attributes up to date.
"""


@shared_task
def update_corporation_alliance(corporation_id):
    esi_operation = EveClient.get_esi_app(
    ).op['get_corporations_corporation_id'](corporation_id=corporation_id)
    response = EveClient.get_esi_client().request(esi_operation)

    if 'alliance_id' not in response.data:
        logger.info(
            "No alliance found for corporation %s, returning None." % corporation_id)
        return None

    alliance_id = response.data['alliance_id']
    eve_corporation = EveCorporation.objects.get(external_id=corporation_id)

    if EveAlliance.objects.filter(external_id=alliance_id).exists():
        eve_corporation.alliance = EveAlliance.objects.get(
            external_id=alliance_id)
    else:
        eve_corporation.alliance = EveAlliance.create_from_external_id(
            alliance_id)

    eve_corporation.save()


@shared_task
def update_corporation_ceo(corporation_id):
    esi_operation = EveClient.get_esi_app(
    ).op['get_corporations_corporation_id'](corporation_id=corporation_id)
    response = EveClient.get_esi_client().request(esi_operation)

    ceo_id = response.data['ceo_id']
    eve_corporation = EveCorporation.objects.get(external_id=corporation_id)
    if EveCharacter.objects.filter(external_id=ceo_id).exists():
        eve_corporation.ceo = EveCharacter.objects.get(external_id=ceo_id)
    else:
        eve_corporation.ceo = EveCharacter.create_from_external_id(ceo_id)

    eve_corporation.save()

@shared_task
def pull_corporation_roster(corporation_id):
    token = EveToken.objects.filter(evecharacter__corporation__external_id=corporation_id).first()
    roster = EveClient.call('get_corporations_corporation_id_members', token=token, corporation_id=corporation_id)
    for character in roster:
        try:
            EveCharacter.create_from_external_id(character)
        except Exception as e:
            logger.warning("Skipping %s in corporation roster" % character)

"""
EveAlliance Tasks
These tasks are used to keep EveAlliance attributes up to date.
"""


@shared_task
def update_alliance_executor(alliance_id):
    esi_operation = EveClient.get_esi_app(
    ).op['get_alliances_alliance_id'](alliance_id=alliance_id)
    response = EveClient.get_esi_client().request(esi_operation)

    if 'executor_corporation_id' not in response.data:
        logger.info(
            "No executor found for alliance %s (likely closed). Returning None." % alliance_id)
        return None

    executor_id = response.data['executor_corporation_id']
    eve_alliance = EveAlliance.objects.get(external_id=alliance_id)

    if EveCorporation.objects.filter(external_id=executor_id).exists():
        eve_alliance.executor = EveCorporation.objects.get(
            external_id=executor_id)
    else:
        eve_alliance.executor = EveCorporation.create_from_external_id(
            executor_id)

    eve_alliance.save()
