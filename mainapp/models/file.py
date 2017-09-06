from django.db import models

from mainapp.models.has_created_and_modified import HasCreatedAndModified


class File(HasCreatedAndModified):
    storage_filename = models.CharField(max_length=256)
    displayed_filename = models.CharField(max_length=1000)

