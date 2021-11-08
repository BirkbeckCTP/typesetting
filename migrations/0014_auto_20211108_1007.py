# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-11-08 10:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('typesetting', '0013_merge_20210205_1049'),
    ]

    operations = [
        migrations.AlterField(
            model_name='typesettingassignment',
            name='display_proof_comments',
            field=models.BooleanField(default=True, help_text='Allow the typesetter to see the proofreading comments'),
        ),
    ]
