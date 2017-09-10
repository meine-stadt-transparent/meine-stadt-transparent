from django.db import models

from .meeting import Meeting
from .paper import Paper


class AgendaItem(models.Model):
    key = models.CharField(max_length=20)
    title = models.CharField(max_length=1000)
    meeting = models.ForeignKey(Meeting)
    # The agenda items of a meeting are ordered by this field
    position = models.IntegerField()
    public = models.NullBooleanField(blank=True)
    paper = models.ForeignKey(Paper, null=True, blank=True)

    def __str__(self):
        return "{}: {} ({})".format(self.meeting.__str__(), self.key, self.position)

    class Meta:
        unique_together = (("meeting", "position"),)
        ordering = ["meeting", "position"]
