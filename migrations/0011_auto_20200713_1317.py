# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-07-13 13:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('typesetting', '0010_auto_20200428_1701'),
    ]

    operations = [
        migrations.AlterField(
            model_name='galleyproofing',
            name='task',
            field=models.TextField(help_text='Add any additional information or instructions for the proofreader here.', verbose_name='Proofing Task'),
        ),
    ]
