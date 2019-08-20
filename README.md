# Django EVE Online Connector
Django EVE Online Connector is a simple Django application that adds models, urls, and Celery tasks to help manage EVE Online entities (characters, corporations, alliances) and ESI SSO.

# Installation
1. Add `django_eveonline_connector` to your INSTALLED_APPS
2. Include the django_eveonline_connector URLs in your urls.py
3. Run `python3 manage.py migrate` to create the django_eveonline_connector models
4. Run `python3 manage.py loaddata initial_scopes` to load the initial ESI scopes

# Provided URLs
| URL Name | Description |
| ------------- | ------------- |
|  django-eveonline-connector-sso-callback   | The callback url for SSO tokens (`sso/callback`)  |
|  django-eveonline-connector-sso-token-add  | Redirects users to the SSO login for EVE Online   |
|  django-eveonline-connector-sso-token-remove  | Removes an SSO token (expects kwarg pk)  |

# Provided Celery Tasks
| Task Name  | Action  |
| ------------- | ------------- |
|  update_characters() | Updates information for all EveCharacter objects  |
|  update_corporations() | Updates information for all EveCorporation objects  |
|  update_alliances() | Updates information for all EveAlliance objects  |