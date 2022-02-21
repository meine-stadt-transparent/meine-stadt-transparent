from django.db import models
from jsonfield import JSONField


class ExternalList(models.Model):
    url = models.CharField(max_length=255, unique=True)
    last_update = models.DateTimeField()

    def __str__(self):
        return f"{self.url} with last update {self.last_update}"


class CachedObject(models.Model):
    url = models.CharField(max_length=255, unique=True)
    data = JSONField()
    oparl_type = models.CharField(max_length=100)
    to_import = models.BooleanField(default=True)

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        return self.url == other.url

    def __str__(self):
        return f"{self.oparl_type}: {self.url} ({self.to_import})"
