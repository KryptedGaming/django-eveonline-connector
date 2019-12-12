from django.apps import AppConfig


class DjangoEveOnlineConnectorConfig(AppConfig):
    name = "django_eveonline_connector"
    verbose_name = "EVE Online Connector"
    url_slug = 'eveonline'

    def ready(self):
        from django.db.models.signals import post_save, post_delete
        from .signals import scope_save, scope_delete
        from django_eveonline_connector.models import EveScope 
        post_save.connect(scope_save, sender=EveScope)
        post_delete.connect(scope_delete, sender=EveScope)