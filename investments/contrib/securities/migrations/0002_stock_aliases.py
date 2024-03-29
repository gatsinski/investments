# Generated by Django 4.0.4 on 2022-11-06 07:46

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("securities", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="stock",
            name="aliases",
            field=models.CharField(
                blank=True,
                help_text="Some brokers don't use the symbols in their reports. If such is the case, list all known aliases separated by comma.",
                max_length=254,
                verbose_name="Aliases",
            ),
        ),
    ]
