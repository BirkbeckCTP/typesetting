# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-01-26 11:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('typesetting', '0011_auto_20200713_1317'),
    ]

    operations = [
        migrations.AddField(
            model_name='typesettingcorrection',
            name='label',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]