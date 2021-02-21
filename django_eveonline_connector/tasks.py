from celery import shared_task
from .models import *
from django.utils import timezone
from django.db.models import Q
from django_eveonline_connector.exceptions import EveMissingScopeException
from django_eveonline_connector.utilities.esi.universe import batch

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
    Update the affiliations for characters.
    Cached for 3600 seconds, so don't run it more frequently than that. 
    """
    character_ids = EveCharacter.objects.all().values_list('external_id', flat=True)
    affiliations = []
    for character_ids_segment in batch(list(character_ids), 999):
        response = EveClient.call(
            'post_characters_affiliation', characters=character_ids)
        if response.status == 200:
            affiliations = affiliations + response.data

    for affiliation in affiliations:
        character_id = affiliation['character_id']
        corporation_id = affiliation['corporation_id']
        if EveCharacter.objects.filter(external_id=character_id, corporation__external_id=corporation_id).exists():
            continue  # no need to update
        else:
            try:
                character = EveCharacter.objects.get(external_id=character_id)
                character.update_character_corporation(
                    corporation_id=corporation_id)
            except Exception:
                logger.exception(
                    f"Failed to update affiliation for {character_id}")


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
def update_characters():
    for eve_character in EveCharacter.objects.all():
        if eve_character.token and eve_character.token.valid and eve_character.corporation and eve_character.corporation.track_characters:
            logger.info(
                f"Queueing batch update tasks for {eve_character.name}")
            update_character.apply_async(args=[eve_character.external_id])


@shared_task
def update_character(character_id):
    eve_character = EveCharacter.objects.get(external_id=character_id)
    # Queue Tasks
    update_character_assets.apply_async(
        args=[eve_character.external_id])

    update_character_contacts.apply_async(
        args=[eve_character.external_id])

    update_character_contracts.apply_async(
        args=[eve_character.external_id])

    update_character_journal.apply_async(
        args=[eve_character.external_id])

    update_character_jumpclones.apply_async(
        args=[eve_character.external_id])

    update_character_skills.apply_async(
        args=[eve_character.external_id])

    update_character_transactions.apply_async(
        args=[eve_character.external_id])

    # Additional Updates
    eve_character.update_character_corporation()
    eve_character.update_character_corporation_roles()


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
            update_corporation.apply_async(args=[eve_corporation.external_id])
        else:
            logger.info(
                f"Skipping corporation update for {eve_corporation.name}: Not Tracked")


@shared_task
def update_corporation(corporation_id):
    corporation = EveCorporation.objects.get(external_id=corporation_id)
    corporation.update_corporation_alliance()
    corporation.update_corporation_ceo()
    corporation.refresh_from_db()
    if not corporation.validate_ceo():
        corporation.track_corporation = False
        corporation.save()
        logger.warning(
            "Tracking has been disabled for {corporation.name} due to invalid CEO token.")

    if corporation.track_corporation:
        corporation.update_related_characters()


@shared_task
def update_alliances():
    for eve_alliance in EveAlliance.objects.all():
        update_alliance.apply_async(args=[eve_alliance.external_id])


@shared_task
def update_alliance(alliance_id):
    eve_alliance = EveAlliance.objects.get(external_id=alliance_id)
    eve_alliance.update_executor_corporation()


@shared_task
def update_structures():
    for eve_corporation in EveCorporation.objects.filter(track_corporation=True):
        try:
            update_corporation_eveentitydata(
                'corporations_corporation_id_structures', EveStructure, eve_corporation.external_id)
        except Exception as e:
            logger.exception(e)


"""
Data Model Tasks
"""


def update_character_eveentitydata(op, data_model, character_id, delete=False):
    """
    Helper method for update_character_??? tasks.
    They basically all follow the same behavior. 
    """
    character = EveCharacter.objects.get(external_id=character_id)

    response = EveClient.call(op, character_id=character.external_id)

    if response.status != 200:
        if response.status in [502, 503, 504]:
            logger.warning(
                f"Skipping batch update {data_model.__name__} for {character_id} due to ESI error")
            return
        else:
            logger.error(
                f"[{response.status}] Failed to batch update {data_model.__name__} for {character_id}: {response.header} {response.data}")
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
    update_character_eveentitydata(
        op, *args, **kwargs, character_id=character_id, data_model=data_model, delete=True)


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


"""
Corporation Tasks
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
            f"[{response.status}] Failed to batch update {data_model.__name__} for {character_id}: {response.header} {response.data}")
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
