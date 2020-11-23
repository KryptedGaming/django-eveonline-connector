from django.apps import AppConfig
from django.apps import apps
from django.urls import reverse
import os 

class DjangoEveOnlineConnectorConfig(AppConfig):
    name = "django_eveonline_connector"
    verbose_name = "EVE Online Connector"
    url_slug = 'eveonline'
    package_name = __import__(name).__package_name__
    version = __import__(name).__version__
    
    ESI_BASE_URL=os.environ.get('ESI_BASE_URL', "")
    ESI_CLIENT_ID=os.environ.get('ESI_CLIENT_ID', "")
    ESI_SECRET_KEY=os.environ.get('ESI_SECRET_KEY', "")
    ESI_CALLBACK_URL=os.environ.get('ESI_CALLBACK_URL', "")

    # DO NOT EDIT 
    ESI_BAD_ASSET_CATEGORIES=[42, 43]

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
        from django_eveonline_connector.models import EveClient 
        from django.db.utils import OperationalError

        # bind to krypted application
        if apps.is_installed('packagebinder'):
            from .bindings import create_bindings
            try:
                create_bindings()
            except Exception as e:
                logger.exception(e)