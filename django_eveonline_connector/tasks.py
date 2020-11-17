from celery import task, shared_task
from .models import *
from django.utils import timezone
from django.db.models import Q

import logging
import pytz
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
def update_tokens():
    EveToken.objects.filter(evecharacter=None).delete()
    for token in EveToken.objects.all():
        token.refresh()

    for token in EveToken.objects.all():
        if token.valid and token.invalidated:
            token.invalidated = None 
            token.save() 
        elif not token.valid and not token.invalidated:
            token.invalidated = timezone.now()
            token.save()
        elif token.invalidated:
            time_passed = timezone.now() - token.invalidated
            if time_passed.days > 7:
                token.delete()

@shared_task
def update_characters(jitter_max=1800):
    for eve_character in EveCharacter.objects.all():
        if eve_character.token and eve_character.token.valid and eve_character.corporation.track_characters: 
            logger.info(f"Queueing batch update tasks for {eve_character.name}")
            jitter = (eve_character.pk*10) % jitter_max
            update_character_assets.apply_async(
                args=[eve_character.external_id],
                countdown=jitter)
                
            update_character_contacts.apply_async(
                args=[eve_character.external_id],
                countdown=jitter)
                
            update_character_contracts.apply_async(
                args=[eve_character.external_id],
                countdown=jitter)
                
            update_character_journal.apply_async(
                args=[eve_character.external_id],
                countdown=jitter)
                
            update_character_jumpclones.apply_async(
                args=[eve_character.external_id],
                countdown=jitter)
                
            update_character_skills.apply_async(
                args=[eve_character.external_id],
                countdown=jitter)
                
            update_character_transactions.apply_async(
                args=[eve_character.external_id],
                countdown=jitter)

@shared_task
def update_character(character_id):
    eve_character = EveCharacter.objects.get(character_id)
    eve_character.update_character_corporation()

    update_character_assets.apply_async(
        args=[eve_character.external_id],
        countdown=jitter)

    update_character_contacts.apply_async(
        args=[eve_character.external_id],
        countdown=jitter)

    update_character_contracts.apply_async(
        args=[eve_character.external_id],
        countdown=jitter)

    update_character_journal.apply_async(
        args=[eve_character.external_id],
        countdown=jitter)

    update_character_jumpclones.apply_async(
        args=[eve_character.external_id],
        countdown=jitter)

    update_character_skills.apply_async(
        args=[eve_character.external_id],
        countdown=jitter)

    update_character_transactions.apply_async(
        args=[eve_character.external_id],
        countdown=jitter)

@shared_task
def update_character_roles():
    for eve_character in EveCharacter.objects.all():
        if eve_character.token and eve_character.token.valid:
            update_character_corporation_roles.apply_async(args=[eve_character.external_id])

@shared_task
def assign_eve_groups():
    for group_rule in EveGroupRule.objects.all():
        for user in group_rule.invalid_user_list:
            logger.info(
                f"Removing group ({group_rule.group} to user ({user})")
            user.groups.remove(group_rule.group)
        for user in group_rule.missing_user_list:
            logger.info(
                f"Adding group ({group_rule.group} to user ({user})")
            user.groups.add(group_rule.group)

@shared_task
def update_corporations():
    for eve_corporation in EveCorporation.objects.all():
        if eve_corporation.evecharacter_set.all().count() == 0:
            eve_corporation.delete()
            continue
        if eve_corporation.track_corporation:
            pull_corporation_roster.apply_async(args=[eve_corporation.external_id])
            update_corporation_alliance.apply_async(
                args=[eve_corporation.external_id])
            update_corporation_ceo.apply_async(
                args=[eve_corporation.external_id])
        else:
            logger.info(f"Skipping corporation update for {eve_corporation.name}: Not Tracked")

@shared_task
def update_alliances():
    for eve_alliance in EveAlliance.objects.all():
        update_alliance_executor.apply_async(args=[eve_alliance.external_id])

@shared_task
def update_structures():
    for eve_corporation in EveCorporation.objects.filter(track_corporation=True):
        try:
            update_corporation_eveentitydata(
                'corporations_corporation_id_structures', EveStructure, eve_corporation.external_id)
        except Exception as e:
            logger.error(e)
"""
Character tasks 
"""
def update_character_eveentitydata(op, data_model, character_id, delete=False):
    """
    Helper method for update_character_??? tasks.
    They basically all follow the same behavior. 
    """
    character = EveCharacter.objects.get(external_id=character_id)

    response = EveClient.call(op, character_id=character.external_id)

    if response.status != 200:
        logger.error(f"Failed to batch update {data_model} for {character_id}: {response.header} {response.data}")
        return

    items = response.data

    if 'X-Pages' in response.header and response.header['X-Pages'][0] > 1:
        for num in range(2, response.header['X-Pages'][0]+1):
            response = EveClient.call(
                op, character_id=character.external_id, page=num)
            if response.status != 200:
                continue 
            items += response.data 

    if len(items) == 0:
        return []

    if delete:
        data_model.objects.filter(entity=character).delete()

    data_model.create_from_esi_response(items, character.external_id)
    
    return items 

@shared_task
def update_character_assets(character_id, *args, **kwargs):
    op = 'get_characters_character_id_assets'
    data_model = EveAsset 
    update_character_eveentitydata(
        op, *args, **kwargs, character_id=character_id, delete=True, data_model=data_model)
    

@shared_task
def update_character_jumpclones(character_id, *args, **kwargs):
    op = 'get_characters_character_id_clones'
    data_model = EveJumpClone
    update_character_eveentitydata(op, *args, **kwargs, character_id=character_id, data_model=data_model, delete=True)


@shared_task 
def update_character_contacts(character_id, *args, **kwargs):
    op = 'get_characters_character_id_contacts'
    data_model = EveContact
    update_character_eveentitydata(
        op, *args, **kwargs, character_id=character_id, data_model=data_model, delete=True)

@shared_task
def update_character_contracts(character_id, *args, **kwargs):
    op = 'get_characters_character_id_contracts'
    data_model = EveContract
    update_character_eveentitydata(
        op, *args, delete=False, **kwargs, character_id=character_id, data_model=data_model)


@shared_task
def update_character_skills(character_id, *args, **kwargs):
    op = 'get_characters_character_id_skills'
    data_model = EveSkill
    response = update_character_eveentitydata(
        op, *args, **kwargs, character_id=character_id, data_model=data_model, delete=True)

    character = EveCharacter.objects.get(external_id=character_id)
    info = EveCharacterInfo.objects.get_or_create(character=character)[0]
    info.skill_points = response['total_sp']
    info.save()
    

@shared_task
def update_character_journal(character_id, *args, **kwargs):
    op = 'get_characters_character_id_wallet_journal'
    data_model = EveJournalEntry
    update_character_eveentitydata(
        op, *args, delete=False, **kwargs, character_id=character_id, data_model=data_model)

@shared_task
def update_character_transactions(character_id, *args, **kwargs):
    op = 'get_characters_character_id_wallet_transactions'
    data_model = EveTransaction
    update_character_eveentitydata(
        op, *args, delete=False, **kwargs, character_id=character_id, data_model=data_model)

@shared_task
def update_character_corporation_roles(character_id):
    character = EveCharacter.objects.get(external_id=character_id)
    eve_client = EveClient.get_instance()
    response = eve_client.call(op='get_characters_character_id_roles', character_id=character_id)
    if response.status != 200:
        logger.error(f"Failed to pull corporation roles for character {character_id}")
        return 
    roles = EveCorporationRole.objects.filter(
        codename__in=response.data['roles'])
    if roles != character.roles.all():
        character.roles.set(roles)
"""
Corporatoin Tasks 
"""


def update_corporation_eveentitydata(op, data_model, corporation_id, delete=False):
    """
    Helper method for update_corporation_??? tasks.
    They basically all follow the same behavior. 
    """

    corporation = EveCorporation.objects.get(external_id=corporation_id)

    response = EveClient.call(op, corporation_id=corporation.external_id)

    if response.status != 200:
        logger.error(
            f"Failed to batch update {data_model} for {character_id}: {response.header} {response.data}")
        return


    items = response.data

    if 'X-Pages' in response.header and response.header['X-Pages'][0] > 1:
        for num in range(2, response.header['X-Pages'][0]+1):
            response = EveClient.call(
                op, corporation_id=corporation.external_id, page=num)
            if response.status != 200:
                continue
            items += response.data

    if len(items) == 0:
        return []

    if delete:
        data_model.objects.filter(entity=corporation).delete()

    data_model.create_from_esi_response(items, corporation.external_id)

    return items

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
       logger.info(f"Skipping CEO update for {eve_corporation.external_id}: CEO not in database")

    eve_corporation.save()

@shared_task
def pull_corporation_roster(corporation_id):
    token = EveToken.objects.filter(evecharacter__corporation__external_id=corporation_id).first()
    roster = EveClient.call('get_corporations_corporation_id_members', token=token, corporation_id=corporation_id)
    members_to_update = EveCharacter.objects.filter(~Q(external_id__in=roster.data))
    ids_that_exist = EveCharacter.objects.filter(external_id__in=roster.data).values_list('external_id', flat=True)

    for character in roster.data:
        if character not in ids_that_exist:
            EveCharacter.create_from_external_id(character)
        else:
            logger.info(f"skipping {character} due to already existing")

    for member in members_to_update:
        member.update_character_corporation()

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
