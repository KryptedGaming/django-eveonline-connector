# User Guide
## Installation 
1. Install `django-eveonline_connector`

    ```
    pip install django_eveonline_connector
    ```

    !!! note
        Krypted Platform users, specify `django_eveonline_connector` in `PIP_INSTALLS`.
    
2. Add `django_eveonline_connector` to your `INSTALLED_APPS`

## Static Database

!!! important
    Krypted Platform users, skip this section. The static database is included in your base image.

The static database is highly recommended, without this many services will be hamstringed by ESI. We recommend the SQLLite database from FuzzWorks.


1. Install BZIP for static export file `apt-get install bzip`
2. Get the export `wget https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2`
3. Decompress `bunzip2 sqlite-latest.sqlite.bz2`
4. Rename (optional) `mv sqlite-latest.sqlite eve_static.sqlite`
5. Add the database to the settings file (eve_static is what the code looks for)

```
DATABASES = {
    'eve_static': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'eve_static_export.sqlite'),
    }
}
```


## Configuration

!!! important
    Krypted Platform users, you will be using Admin Panel settings to configure your package. Navigate to **Admin Panel** from your homepage sidebar, edit settings under the **Django EVE Connector** section.


There are two ways to configure `django_eveonline_connector`:

1. Environment Variables
2. Admin Panel Settings 

|  Variable  |  Description  |  Example  |
|:---|:--:|:--:|
|  `ESI_BASE_URL`      |  ESI Swagger Version  |  `https://esi.evetech.net/latest/swagger.json?datasource=tranquility`  |
|  `ESI_CLIENT_ID`     |  Client ID from Developer Application  |  `1239812934871239`  |
|  `ESI_SECRET_KEY`    |  Secret Key from Developer Application  | `aiosdfjasodjifajoi234aisdfa`   |
|  `ESI_CALLBACK_URL`  |  Callback URL from Developer Application  |  http://**MY.DOMAIN**/eveonline/sso/callback  |

To create a developer application, navigate [here](https://developers.eveonline.com/applications). 

1. Log in and create a new application
2. Select **Authentication & API Access** and select all scopes 
3. Insert your callback URL (e.g http://**MY.DOMAIN**/eveonline/sso/callback)
4. Save the application

Use the fields from the application to fill out the settings from above. 

## Permissions
Your user groups will need permissions to interact with certain parts of the application. 

### General Permissions
|  Permission Class  |  Action  |  Result  |
|:---|:--:|:--:|
| eve scope | CRUD | User with staff status can modify scope settings |
| eve character | View | User can view EVE characters | 
| eve character | Change | User can refresh EVE character data | 
| eve character | Delete | User with staff status can delete EVE Characters | 
| eve corporation | View | User can view tracked corporations | 
| eve alliance | View | User can view tracked alliances | 
| eve asset | View | User can view character assets (requires eve character view) | 
| eve jump clone | View | User can view character clones | 
| eve contact | View | User can view eve character contacts | 
| eve contract | View | User can view eve character contracts | 
| eve skill | View | User can view eve character skills | 
| eve journal entry | View | User can view eve character journal entries | 
| eve transaction | View | User can view eve character transactions |
| eve structure | View | User can view eve corporation structures (only their corporation) |

### Special Permissions 
| Permission Class | Additional Permission | 
|:---|:--:|
| eve structure | Corporation bypass (can view all structures) | 

## General Usage
### Tracking Corporations
By default, we do not automatically keep all entity data up to date. To track a corporation and its related data (structures, etc), be sure to toggle `track_corporation` on the corporation in the **Admin Panel.**

To constantly keep the character data (skills, contracts, etc) up to date for members of a corporation, enable `track_characters`. 

### Optional Tasks

!!! danger
    Only applies to Krypted users.

There are additional tasks that you can enable, such as structure tracking. Make sure you visit **Setup** in the Krypted Platform sidebar. 

### Group Rules 
Group rules are rules that apply a Django group based on characters, corporations, and more. You can add these in the **Admin Panel**. 

