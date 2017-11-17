from django.db import models

from mainapp.models.file import File
from mainapp.models.consultation import Consultation
from .default_fields import SoftDeleteModelManager, SoftDeleteModelManagerWithDeleted
from .meeting import Meeting


class AgendaItem(models.Model):
    oparl_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    key = models.CharField(max_length=20)
    title = models.TextField()
    meeting = models.ForeignKey(Meeting)
    consultation = models.ForeignKey(Consultation, null=True, blank=True)
    # The agenda items of a meeting are ordered by this field
    position = models.IntegerField()
    public = models.NullBooleanField(blank=True)
    result = models.CharField(max_length=200, null=True, blank=True)
    resolution_text = models.TextField(null=True, blank=True)
    resolution_file = models.ForeignKey(File, null=True, blank=True, related_name="resolution_file")
    auxiliary_file = models.ManyToManyField(File, blank=True, related_name="auxiliary_file")
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    objects = SoftDeleteModelManager()
    objects_with_deleted = SoftDeleteModelManagerWithDeleted()

    def __str__(self):
        return "{} {} ({}. {})".format(self.key, self.title, self.position, self.meeting.__str__())

    class Meta:
        ordering = ["meeting", "position"]
