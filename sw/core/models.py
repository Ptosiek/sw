from django.db import models
from django.utils import timezone


class Collection(models.Model):
    class Type(models.IntegerChoices):
        PLANET = 1, "Planet"
        PEOPLE = 2, "People"

    created = models.DateTimeField(default=timezone.now, db_index=True)
    file = models.FileField()
    type = models.IntegerField(choices=Type.choices)

    nb_records = models.IntegerField(default=0)

    class Meta:
        ordering = ["-created"]
        get_latest_by = ["created"]

    def __str__(self):
        return f"{self.get_type_display().lower()}: {self.created}"
