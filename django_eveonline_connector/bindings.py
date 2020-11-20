from django.apps import apps 
from django.urls import reverse
from django.conf import settings
from .models import EveClient
from .forms import EveClientForm
from packagebinder.bind import PackageBinding, SettingsBinding, TaskBinding, SidebarBinding
import logging 

logger = logging.getLogger(__name__)

app_config = apps.get_app_config('django_eveonline_connector')

package_binding = PackageBinding(
    package_name=app_config.name, 
    version=app_config.version, 
    url_slug='eveonline', 
)

settings_binding = SettingsBinding(
    package_name=app_config.name, 
    settings_class=EveClient,
    settings_form=EveClientForm,
)

task_binding = TaskBinding(
    package_name=app_config.name, 
    required_tasks = [
        {
            "name": "EVE: Update Tokens",
            "task_name": "django_eveonline_connector.tasks.update_tokens",
            "interval": 1,
            "interval_period": "days",
        },
        {
            "name": "EVE: Update Characters",
            "task_name": "django_eveonline_connector.tasks.update_characters",
            "interval": 1,
            "interval_period": "days",
        },
        {
            "name": "EVE: Update Corporations",
            "task_name": "django_eveonline_connector.tasks.update_corporations",
            "interval": 1,
            "interval_period": "days",
        },
        {
            "name": "EVE: Update Affilitions",
            "task_name": "django_eveonline_connector.tasks.update_tokens",
            "interval": 5,
            "interval_period": "minutes",
        }
    ],
    optional_tasks = [
        {
            "name": "EVE: Update Structures",
            "task_name": "django_eveonline_connector.tasks.update_structures",
            "interval": 1,
            "interval_period": "days",
        },
        {
            "name": "EVE: Update Character Corporation Roles",
            "task_name": "django_eveonline_connector.tasks.update_character_roles",
            "interval": 1,
            "interval_period": "days",
        },
        {
            "name": "EVE: Assign Eve Groups",
            "task_name": "django_eveonline_connector.tasks.assign_eve_groups",
            "interval": 30,
            "interval_period": "minutes",
        }
    ]
)

sidebar_binding = SidebarBinding(
    package_name=app_config.name,
    parent_menu_item={
        "fa_icon": 'fa-meteor',
        "name": "EVE Online",
        "url": None, 
    },
    child_menu_items=[
        {
            "fa_icon": "fa-users",
            "name": "Characters",
            "url": reverse("django-eveonline-connector-characters-view"),
        },
        {
            "fa_icon": "fa-landmark",
            "name": "Corporations",
            "url": reverse("django-eveonline-connector-corporations-view"),
        },
    ]
)

def create_bindings():
    try:
        package_binding.save()
        settings_binding.save()
        task_binding.save()
        sidebar_binding.save()
    except Exception as e:
        if settings.DEBUG:
            raise(e)
        else:
            logger.error(f"Failed package binding step for {app_config.name}: {e}")
