# Overview

Django module that supplies models, tasks, and fuctions for EVE Online. Primarily for use in the [Krypted Platform](https://kryptedgaming.github.io/krypted/). 

## Project layout
```
├── __init__.py
├── admin.py                # Admin views for Django
├── apps.py                 
├── decorators.py           # View and function decorators
├── exceptions.py           # Custom exceptions
├── models.py               # Data models 
├── tasks.py                # Celery tasks
├── templates               # Templates (built with AdminLTE 2.0 in mind)
├── tests                   # Test cases
├── urls.py                 # URLs
├── utilities               # EVE Online static and ESI utilities
│   ├── __init__.py
│   ├── esi                 # ESI helpers
│   │   ├── __init__.py
│   │   └── universe.py
│   └── static              # EVE Static Database helpers
│       ├── __init__.py
│       └── universe.py
└── views                   # Django views
    ├── __init__.py
    ├── api.py
    ├── character.py
    ├── corporation.py
    └── sso.py
```