from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.db import transaction
from .models import EveCharacter, EveCorporation, EveAlliance
from .tasks import update_character, update_corporation, update_alliance


@receiver(post_save, sender=EveCharacter)
def update_character_information(sender, **kwargs):
    def call():
        entity = kwargs.get('instance')
        created = kwargs.get('created')
        if created:
            update_character.apply_async(
                args=[entity.external_id])

    transaction.on_commit(call)


@receiver(post_save, sender=EveCorporation)
def update_corporation_information(sender, **kwargs):
    def call():
        entity = kwargs.get('instance')
        created = kwargs.get('created')
        if created:
            update_corporation.apply_async(
                args=[entity.external_id])

    transaction.on_commit(call)


@receiver(post_save, sender=EveAlliance)
def update_alliance_information(sender, **kwargs):
    def call():
        entity = kwargs.get('instance')
        created = kwargs.get('created')
        if created:
            update_alliance.apply_async(
                args=[entity.external_id])

    transaction.on_commit(call)
