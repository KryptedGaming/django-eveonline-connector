=====
Django EVE Online Connector
=====

Django EVE Online Connector is a simple Django application that adds
EVE Online entities and SSO urls to your application. 

Quick start
-----------

1. Add "django_eveonline_connector" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'django_eveonline_connector',
    ]

2. Include the django_eveonline_connector URLconf in your project urls.py like this::

    path('eveonline/', include('django_eveonline_connector.urls')),

3. Run `python manage.py migrate` to create the django_eveonline_connector models.

4. Start the development server and visit http://127.0.0.1:8000/admin/
   to create your EveClient object from https://developers.eveonline.com/applications

5. Use the SSO methods in your application to allow users to add characters, corporations, and alliances 

Urls 
-----------
django-eveonline-connector-sso-callback
django-eveonline-connector-sso-token-add
django-eveonline-connector-sso-token-remove