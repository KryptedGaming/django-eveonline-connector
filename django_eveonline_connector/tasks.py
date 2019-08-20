from celery import task, shared_task
from django_eveonline_connector.models import EveClient, EveCharacter, EveCorporation, EveAlliance

import logging
logger = logging.getLogger(__name__)

"""
Global Tasks
These are what users register to maintain up-to-date EveEntity information.
"""
@shared_task
def update_characters():
    for eve_character in EveCharacter.objects.all():
        update_character_portrait.apply_async(args=[eve_character.external_id])
        update_character_corporation.apply_async(
            args=[eve_character.external_id])


@shared_task
def update_corporations():
    for eve_corporation in EveCorporation.objects.all():
        update_corporation_alliance.apply_async(
            args=[eve_corporation.external_id])
        update_corporation_ceo.apply_async(
            args=[eve_corporation.external_id])


@shared_task
def update_alliances():
    for eve_alliance in EveAlliance.objects.all():
        update_alliance_executor.apply_async(args=[eve_alliance.external_id])


"""
EveCharacter Tasks
These tasks are used to keep EveCharacter attributes up to date.
"""


@shared_task
def update_character_portrait(character_id):
    esi_operation = EveClient.get_esi_app(
    ).op['get_characters_character_id_portrait'](character_id=character_id)
    response = EveClient.get_esi_client().request(esi_operation)

    if 'px64x64' not in response.data:
        raise Exception(
            "Portrait (px64x64) not found in response for character_id %s" % character_id)

    eve_character = EveCharacter.objects.get(external_id=character_id)
    eve_character.portrait = response.data['px64x64'].replace("http", "https")
    eve_character.save()


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
