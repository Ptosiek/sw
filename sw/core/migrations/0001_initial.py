from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Collection",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(
                        db_index=True, default=django.utils.timezone.now
                    ),
                ),
                ("file", models.FileField(upload_to="")),
                ("type", models.IntegerField(choices=[(1, "Planet"), (2, "People")])),
                ("nb_records", models.IntegerField(default=0)),
            ],
            options={
                "ordering": ["-created"],
                "get_latest_by": ["created"],
            },
        ),
    ]
