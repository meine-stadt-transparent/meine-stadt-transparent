from django.db import models

from mainapp.models.consultation import Consultation
from mainapp.models.file import File
from .helper import DefaultFields
from .meeting import Meeting


class AgendaItem(DefaultFields):
    key = models.CharField(max_length=20, null=True, blank=True)
    name = models.TextField()
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE)
    consultation = models.ForeignKey(
        Consultation, null=True, blank=True, on_delete=models.CASCADE
    )
    # The agenda items of a meeting are ordered by this field
    position = models.IntegerField()
    public = models.BooleanField(null=True, blank=True)
    result = models.TextField(null=True, blank=True)
    resolution_text = models.TextField(null=True, blank=True)
    resolution_file = models.ForeignKey(
        File,
        null=True,
        blank=True,
        related_name="resolution_file",
        on_delete=models.CASCADE,
    )
    auxiliary_file = models.ManyToManyField(
        File, blank=True, related_name="auxiliary_file"
    )
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return "{}: {} ({}. {})".format(
            self.key, self.name, self.position, self.meeting
        )

    class Meta:
        ordering = ["meeting", "position"]
