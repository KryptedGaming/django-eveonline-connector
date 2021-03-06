# Generated by Django 2.2.10 on 2020-09-28 00:13

from django.db import migrations, models
import django_eveonline_connector.models


class Migration(migrations.Migration):

    dependencies = [
        ('django_eveonline_connector', '0029_load_required_scopes'),
    ]

    operations = [
        migrations.AddField(
            model_name='evetoken',
            name='invalidated',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='evetoken',
            name='requested_scopes',
            field=models.ManyToManyField(blank=True, default=django_eveonline_connector.models.EveScope.get_required, related_name='requested_scopes', to='django_eveonline_connector.EveScope'),
        ),
        migrations.AlterField(
            model_name='evescope',
            name='name',
            field=models.CharField(max_length=128, unique=True),
        ),
    ]
