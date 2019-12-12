from django.contrib.auth.models import User, Group
from django_eveonline_connector.models import EveScope, EveClient
from django.dispatch import receiver
from django.db.models.signals import post_delete, post_save
from django.db import transaction
from django.core.exceptions import PermissionDenied

import logging
logger = logging.getLogger(__name__)

@receiver(post_save, sender=EveScope)
def scope_save(sender, **kwargs):
    def call():
        EveClient.get_instance().save()
    transaction.on_commit(call)

@receiver(post_delete, sender=EveScope)
def scope_delete(sender, **kwargs):
    def call():
        EveClient.get_instance().save()
    transaction.on_commit(call)