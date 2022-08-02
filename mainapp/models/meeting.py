import pytz
from django.conf import settings
from django.db import models
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from icalendar import Event

from .file import File
from .helper import DefaultFields, ShortableNameFields
from .location import Location
from .organization import Organization
from .person import Person

PUBLICALITY = (
    (0, "unknown"),
    (1, "public"),
    (2, "not public"),
    # Most meeting consist of a public and a subsequent private part
    (3, "splitted"),
)


class Meeting(DefaultFields, ShortableNameFields):
    cancelled = models.BooleanField(default=False)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    location = models.ForeignKey(
        Location, null=True, blank=True, on_delete=models.CASCADE
    )
    # There are cases where mutliple organizations have a joined official meeting
    organizations = models.ManyToManyField(Organization, blank=True)
    # Only applicable when there are participants without an organization
    persons = models.ManyToManyField(Person, blank=True)
    invitation = models.ForeignKey(
        File,
        null=True,
        blank=True,
        related_name="meeting_invitation",
        on_delete=models.CASCADE,
    )
    results_protocol = models.ForeignKey(
        File,
        null=True,
        blank=True,
        related_name="meeting_results_protocol",
        on_delete=models.CASCADE,
    )
    verbatim_protocol = models.ForeignKey(
        File,
        null=True,
        blank=True,
        related_name="meeting_verbatim_protocol",
        on_delete=models.CASCADE,
    )
    # Sometimes there are additional files atttached to a meeting
    auxiliary_files = models.ManyToManyField(
        File, blank=True, related_name="meeting_auxiliary_files"
    )
    public = models.IntegerField(choices=PUBLICALITY, default=0, blank=True)

    def as_ical_event(self) -> Event:
        url = settings.ABSOLUTE_URI_BASE + reverse("meeting", args=[self.id])
        event = Event()
        event.add("uid", "meeting-{}@{}".format(self.id, settings.REAL_HOST))
        event.add("summary", self.short_name)
        event.add("description", self.name + "\n" + url)
        # https://stackoverflow.com/questions/854036/html-in-ical-attachment
        # https://docs.microsoft.com/en-us/openspecs/exchange_server_protocols/ms-oxcical/d7f285da-9c7a-4597-803b-b74193c898a8
        html_desc = render_to_string(
            "mainapp/meeting_ical_alt_desc.html", {"description": self.name, "url": url}
        ).strip()
        event.add("X-ALT-DESC;FMTTYPE=text/html", html_desc)
        # Really ugly ugly backporting to pytz after django switched away from it
        # TODO: Figure out if we can get icalendar and zoneinfo to harmonize
        event.add(
            "dtstart",
            timezone.localtime(self.start).astimezone(
                pytz.timezone(settings.TIME_ZONE)
            ),
        )
        event.add("url", url)
        if self.end:
            event.add(
                "dtend",
                timezone.localtime(self.end).astimezone(
                    pytz.timezone(settings.TIME_ZONE)
                ),
            )

        if self.location and self.location.description:
            event.add("location", self.location.description)

        if self.cancelled:
            event.add("method", "CANCEL")
            event.add("status", "CANCELLED")

        return event

    def __str__(self):
        return self.short_name

    def get_default_link(self):
        return reverse("meeting", args=[self.id])

    def sort_date(self):
        return self.start
