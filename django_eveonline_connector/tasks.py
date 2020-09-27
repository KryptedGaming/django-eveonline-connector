from celery import task, shared_task
from .models import *

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
def update_characters():
    for eve_character in EveCharacter.objects.all():
        if eve_character.token: 
            update_character_assets.apply_async(args=[eve_character.character_id])
            update_character_contacts.apply_async(args=[eve_character.character_id])
            update_character_contracts.apply_async(args=[eve_character.character_id])
            update_character_journal.apply_async(args=[eve_character.character_id])
            update_character_jumpclones.apply_async(args=[eve_character.character_id])
            update_character_skills.apply_async(args=[eve_character.character_id])
            update_character_transactions.apply_async(args=[eve_character.character_id])

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
Character tasks 
"""
def update_character_eveentitydata(op, *args, delete=True, **kwargs):
    """
    Helper method for update_character_??? tasks.
    They basically all follow the same behavior. 
    """
    if 'data_model' not in kwargs:
        raise Exception("Must pass an EveEntityData model")

    data_model = kwargs.get('data_model')

    if 'character_id' in kwargs:
        characters = EveCharacter.objects.filter(
            external_id=kwargs.get('character_id'))
    else:
        characters = []
        tokens = EveToken.objects.filter(
            scopes__in=EveClient.get_required_scopes(op))
        for token in tokens:
            characters.append(token.evecharacter)

    for character in characters:
        try:
            response = EveClient.call(op, character_id=character.external_id)
        except Exception as e:
            logger.exception(e)
            continue

        if response.status != 200:
            logger.error(response)
            continue

        items = response.data
        if delete:
            data_model.objects.filter(entity=character).delete()
        data_model.create_from_esi_response(items, character.external_id)

@shared_task
def update_character_assets(character_id=None, *args, **kwargs):
    """
    Updates all character assets from ESI.
    Highly recommended to not use this frequently, unless you absolutely need it.
    """
    op = 'get_characters_character_id_assets'
    data_model = EveAsset 
    update_character_eveentitydata(
        op, *args, **kwargs, character_id=character_id, data_model=data_model)

@shared_task
def update_character_jumpclones(character_id, *args, **kwargs):
    op = 'get_characters_character_id_clones'
    data_model = EveJumpClone
    update_character_eveentitydata(op, *args, **kwargs, character_id=character_id, data_model=data_model)

@shared_task 
def update_character_contacts(*args, **kwargs):
    op = 'get_characters_character_id_contacts'
    data_model = EveContact
    update_character_eveentitydata(op, *args, **kwargs, data_model=data_model)

@shared_task
def update_character_contracts(*args, **kwargs):
    op = 'get_characters_character_id_contracts'
    data_model = EveContract
    update_character_eveentitydata(op, *args, delete=False, **kwargs, data_model=data_model)


@shared_task
def update_character_skills(*args, **kwargs):
    op = 'get_characters_character_id_skills'
    data_model = EveSkill
    update_character_eveentitydata(op, *args, **kwargs, data_model=data_model)

@shared_task
def update_character_journal(*args, **kwargs):
    op = 'get_characters_character_id_wallet_journal'
    data_model = EveJournalEntry
    update_character_eveentitydata(op, *args, delete=False, **kwargs, data_model=data_model)

@shared_task
def update_character_transactions(*args, **kwargs):
    op = 'get_characters_character_id_wallet_transactions'
    data_model = EveTransaction
    update_character_eveentitydata(op, *args, delete=False, **kwargs, data_model=data_model)

"""
Helper Tasks
"""
@shared_task
def update_corporation_alliance(corporation_id):
    """
    Legacy method that will be deprecated. Use update_affiliations().
    """
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
