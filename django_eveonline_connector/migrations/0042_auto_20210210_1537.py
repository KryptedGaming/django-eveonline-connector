# Generated by Django 2.2.13 on 2021-02-10 15:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('django_eveonline_connector', '0041_auto_20201130_1743'),
    ]

    operations = [
        migrations.AlterField(
            model_name='evecharacter',
            name='token',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='django_eveonline_connector.EveToken'),
        ),
        migrations.AlterField(
            model_name='evecontract',
            name='issuer_corporation_name',
            field=models.CharField(max_length=256),
        ),
    ]
