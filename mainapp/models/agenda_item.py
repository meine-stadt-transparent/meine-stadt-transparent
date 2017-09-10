from django.db import models

from .meeting import Meeting
from .paper import Paper


class AgendaItem(models.Model):
    key = models.CharField(max_length=20)
    meeting = models.ForeignKey(Meeting)
    # The agenda items of a meeting are ordered by this field
    position = models.IntegerField()
    public = models.NullBooleanField(blank=True)
    paper = models.ForeignKey(Paper)

    class Meta:
        unique_together = (("meeting", "position"),)
        ordering = ['position']
