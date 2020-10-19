from django.apps import AppConfig
from django.apps import apps
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
        try:
            if not EveClient.objects.all().exists():
                EveClient().save()
        except OperationalError:
            # assume we're in migration phase
            pass 

        # bind to krypted application
        if apps.is_installed('packagebinder'):
            from packagebinder.bind import BindObject
            bind = BindObject(self.package_name, self.version)
            # Required Task Bindings
            bind.add_required_task(
                name="EVE: Update Tokens",
                task="django_eveonline_connector.tasks.update_tokens",
                interval=1,
                interval_period="days",
            )
            bind.add_required_task(
                name="EVE: Update Characters",
                task="django_eveonline_connector.tasks.update_characters",
                interval=1,
                interval_period="days",
            )
            bind.add_required_task(
                name="EVE: Update Corporations",
                task="django_eveonline_connector.tasks.update_corporations",
                interval=1,
                interval_period="days",
            )
            bind.add_required_task(
                name="EVE: Update Affilitions",
                task="django_eveonline_connector.tasks.update_tokens",
                interval=5,
                interval_period="minutes",
            )
            # Optional Task Bindings 
            bind.add_optional_task(
                name="EVE: Update Structures",
                task="django_eveonline_connector.tasks.update_structures",
                interval=1,
                interval_period="days",
            )
            bind.save()
