from django.db import models

from .committee import Committee
from .default_fields import DefaultFields
from .location import Location


class Meeting(DefaultFields):
    name = models.CharField(max_length=1000)
    cancelled = models.BooleanField()
    start = models.DateTimeField()
    end = models.DateTimeField()
    locations = models.ForeignKey(Location, null=True, blank=True)
    # There are cases where mutliple committes have a joined official meeting
    committees = models.ManyToManyField(Committee)
