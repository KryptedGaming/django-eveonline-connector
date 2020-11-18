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

        # bind to krypted application
        if apps.is_installed('packagebinder'):
            from packagebinder.exceptions import BindException
            try:
                bind = apps.get_app_config('packagebinder').get_bind_object(
                    self.package_name, self.version)
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
                bind.add_optional_task(
                    name="EVE: Update Character Corporation Roles",
                    task="django_eveonline_connector.tasks.update_character_roles",
                    interval=1,
                    interval_period="days",
                )
                bind.add_optional_task(
                    name="EVE: Assign Eve Groups",
                    task="django_eveonline_connector.tasks.assign_eve_groups",
                    interval=30,
                    interval_period="minutes",
                )
                bind.save()
            except BindException as e:
                print(e)
                return 
            except Exception as e:
                print(e)
                return
