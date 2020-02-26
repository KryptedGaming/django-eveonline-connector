from django.apps import AppConfig

class DjangoEveOnlineConnectorConfig(AppConfig):
    name = "django_eveonline_connector"
    verbose_name = "EVE Online Connector"
    url_slug = 'eveonline'
    
    # required scopes from the package. replaced by queryset after apps load
    required_scopes = ['publicData']

    def ready(self):
        from django.db.models.signals import m2m_changed, post_save, post_delete
        from .signals import eve_token_type_scopes_updated, eve_token_type_save, eve_token_generate_default_token
        from django_eveonline_connector.models import EveTokenType 
        m2m_changed.connect(eve_token_type_scopes_updated, sender=EveTokenType)
        post_save.connect(eve_token_type_save, sender=EveTokenType)
        post_delete.connect(eve_token_generate_default_token, sender=EveTokenType)
        from django_eveonline_connector.models import EveScope 
        self.required_scopes = EveScope.objects.filter(name__in=self.required_scopes)