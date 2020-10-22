# Generated by Django 2.2.13 on 2020-10-18 16:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_eveonline_connector', '0036_auto_20201004_0148'),
    ]

    operations = [
        migrations.AlterField(
            model_name='evecontract',
            name='acceptor_id',
            field=models.BigIntegerField(),
        ),
        migrations.AlterField(
            model_name='evecontract',
            name='assignee_id',
            field=models.BigIntegerField(),
        ),
        migrations.AlterField(
            model_name='evecontract',
            name='contract_id',
            field=models.BigIntegerField(unique=True),
        ),
        migrations.AlterField(
            model_name='evecontract',
            name='issuer_corporation_id',
            field=models.BigIntegerField(),
        ),
        migrations.AlterField(
            model_name='evecontract',
            name='issuer_id',
            field=models.BigIntegerField(),
        ),
    ]