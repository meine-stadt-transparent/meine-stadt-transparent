from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from icalendar import Event

from .organization import Organization
from .default_fields import DefaultFields
from .file import File
from .location import Location
from .person import Person

PUBLICALITY = (
    (0, "unknown"),
    (1, "public"),
    (2, "not public"),
    # Most meeting consist of a public and a subsequent private part
    (3, "splitted"),
)


class Meeting(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    cancelled = models.BooleanField()
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    location = models.ForeignKey(Location, null=True, blank=True)
    # There are cases where mutliple organizations have a joined official meeting
    organizations = models.ManyToManyField(Organization, blank=True)
    # Only applicable when there are participants without an organization
    persons = models.ManyToManyField(Person, blank=True)
    invitation = models.ForeignKey(File, null=True, blank=True, related_name="meeting_invitation")
    results_protocol = models.ForeignKey(File, null=True, blank=True, related_name="meeting_results_protocol")
    verbatim_protocol = models.ForeignKey(File, null=True, blank=True, related_name="meeting_verbatim_protocol")
    # Sometimes there are additional files atttached to a meeting
    auxiliary_files = models.ManyToManyField(File, blank=True, related_name="meeting_auxiliary_files")
    public = models.IntegerField(choices=PUBLICALITY, default=0, blank=True)

    def as_ical_event(self):
        event = Event()
        event.add("uid", "meeting-{}@{}".format(self.id, settings.REAL_HOST))
        event.add("summary", self.short_name)
        event.add("description", self.name)
        event.add("dtstart", timezone.localtime(self.start))
        event.add("dtend", timezone.localtime(self.end))

        if self.location:
            event.add("location", self.location.name)

        if self.cancelled:
            event.add("method", "CANCEL")
            event.add("status", "CANCELLED")

        return event

    def __str__(self):
        return self.short_name

    def get_default_link(self):
        return reverse('meeting', args=[self.id])
