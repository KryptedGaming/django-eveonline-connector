# Generated by Django 2.2.13 on 2020-10-04 01:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('django_eveonline_connector', '0035_auto_20201004_0130'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='evestructure',
            options={'permissions': [('bypass_corporation_view_requirements', "Can view a corporation's structures regardless of current membership")]},
        ),
    ]
