from django.db import models

from mainapp.models.default_fields import DefaultFields


class File(DefaultFields):
    storage_filename = models.CharField(max_length=256)
    displayed_filename = models.CharField(max_length=1000)
    legal_date = models.DateField()
    filesize = models.IntegerField()

