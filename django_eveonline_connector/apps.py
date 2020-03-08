from django.apps import AppConfig
import os 

class DjangoEveOnlineConnectorConfig(AppConfig):
    name = "django_eveonline_connector"
    verbose_name = "EVE Online Connector"
    url_slug = 'eveonline'
    
    ESI_BASE_URL=os.environ.get('ESI_BASE_URL', "")
    ESI_CLIENT_ID=os.environ.get('ESI_CLIENT_ID', "")
    ESI_SECRET_KEY=os.environ.get('ESI_SECRET_KEY', "")
    ESI_CALLBACK_URL=os.environ.get('ESI_CALLBACK_URL', "")

    # DO NOT EDIT 
    ESI_BAD_ASSET_CATEGORIES=[42, 43]
    required_scopes = ['publicData']

    EVEWHO_CONFIG = {
        'domain': 'evewho.com'
    }

    EVEIMG_CONFIG = {
        'domain': 'images.evetech.net',
        'portrait_mapping': {
            'character': 'portrait',
            'corporation': 'logo',
            'alliance': 'logo',
        }
    }

    def ready(self):
        from django.db.models.signals import m2m_changed, post_save, post_delete
        from .signals import eve_token_type_scopes_updated, eve_token_type_save, eve_token_generate_default_token
        from django_eveonline_connector.models import EveTokenType, EveScope
        m2m_changed.connect(eve_token_type_scopes_updated, sender=EveTokenType)
        post_save.connect(eve_token_type_save, sender=EveTokenType)
        post_delete.connect(eve_token_generate_default_token, sender=EveTokenType)

        
        from django_eveonline_connector.models import EveScope 
        self.required_scopes = EveScope.objects.filter(name__in=self.required_scopes)