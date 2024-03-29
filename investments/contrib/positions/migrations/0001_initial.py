# Generated by Django 3.2.10 on 2021-12-28 18:35

import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("brokers", "0001_initial"),
        ("securities", "0001_initial"),
        ("tags", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Position",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated at"),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                (
                    "position_id",
                    models.CharField(
                        help_text="The unique position ID used to identify this position within broker's platform.",
                        max_length=254,
                        verbose_name="ID",
                    ),
                ),
                (
                    "units",
                    models.DecimalField(
                        decimal_places=6,
                        max_digits=16,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Units",
                    ),
                ),
                (
                    "open_price",
                    models.DecimalField(
                        decimal_places=6,
                        max_digits=16,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Open price",
                    ),
                ),
                (
                    "close_price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=6,
                        max_digits=16,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Close price",
                    ),
                ),
                ("opened_at", models.DateTimeField(verbose_name="Opened at")),
                (
                    "closed_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Closed at"
                    ),
                ),
                (
                    "notes",
                    models.CharField(blank=True, max_length=1024, verbose_name="Notes"),
                ),
                (
                    "broker",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="positions",
                        to="brokers.broker",
                    ),
                ),
                (
                    "security",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="positions",
                        to="securities.security",
                    ),
                ),
                (
                    "tags",
                    models.ManyToManyField(
                        related_name="securities",
                        to="tags.Tag",
                        verbose_name="Tags",
                        blank=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "Position",
                "verbose_name_plural": "Positions",
                "unique_together": {("position_id", "broker")},
            },
        ),
    ]
