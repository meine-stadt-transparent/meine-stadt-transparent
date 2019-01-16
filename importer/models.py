from django.db import models
from jsonfield import JSONField

from mainapp.models import File


class ExternalList(models.Model):
    url = models.CharField(max_length=255, unique=True)
    last_update = models.DateTimeField()


class CachedObject(models.Model):
    url = models.CharField(max_length=255, unique=True)
    data = JSONField()
    oparl_type = models.CharField(max_length=100)
    to_import = models.BooleanField(default=True)

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        return self.url == other.url
