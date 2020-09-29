# Django EVE Online Connector
Django EVE Online Connector is a simple Django application that adds models, urls, and Celery tasks to help manage EVE Online entities (characters, corporations, alliances) and ESI SSO.

# Installation
1. Add `django_eveonline_connector` to your INSTALLED_APPS
2. Include the django_eveonline_connector URLs in your urls.py
3. Run `python3 manage.py migrate` to create the django_eveonline_connector models

# Static Database
The static database is highly recommended, without this many services will be hamstringed by ESI. We recommend the SQLLite database from FuzzWorks. 

The example installation assumes you are in the `krypted/app` folder.

1. Install BZIP for static export file `apt-get install bzip
2. Get the export `wget https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2`
3. Decompress `bunzip2 sqlite-latest.sqlite.bz2`
4. Rename (optional) `mv sqlite-latest.sqlite eve_static.sqlite`
5. Add the database to the settings file (`eve_static` is what the code looks for)

```
DATABASES = {
    'eve_static': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'eve_static_export.sqlite'),
    }
}
```

# Provided URLs
| URL Name | Description |
| ------------- | ------------- |
|  django-eveonline-connector-sso-callback   | The callback url for SSO tokens (`sso/callback`)  |
|  django-eveonline-connector-sso-token-type-select  | Redirects users to the SSO login for EVE Online   |
|  django-eveonline-connector-sso-token-remove  | Removes an SSO token (expects kwarg pk)  |

# Provided Celery Tasks
| Task Name  | Action  |
| ------------- | ------------- |
|  update_characters() | Updates information for all EveCharacter objects  |
|  update_corporations() | Updates information for all EveCorporation objects  |
|  update_alliances() | Updates information for all EveAlliance objects  |