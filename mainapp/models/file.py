from datetime import datetime
from typing import Optional, List, Dict, Any

from dateutil import tz
from django.db import models
from django.urls import reverse

from mainapp.functions.minio import minio_client, minio_file_bucket
from .helper import DefaultFields
from .location import Location
from .person import Person

# Assumption: This is older than the oldest data
fallback_date = datetime(1995, 1, 1, 0, 0, 0, tzinfo=tz.tzlocal())


class File(DefaultFields):
    name = models.CharField(max_length=200)
    filename = models.CharField(max_length=200)
    # https://stackoverflow.com/a/643772/3549270#comment11618045_643772
    mime_type = models.CharField(max_length=255)
    legal_date = models.DateField(null=True, blank=True)
    sort_date = models.DateTimeField(default=fallback_date)
    filesize = models.IntegerField(null=True, blank=True)
    locations = models.ManyToManyField(Location, blank=True)
    mentioned_persons = models.ManyToManyField(Person, blank=True)
    page_count = models.IntegerField(null=True, blank=True)
    parsed_text = models.TextField(null=True, blank=True)
    # In case the license is different than the rest of the system, e.g. a CC-licensed picture
    license = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    # Sometimes we need to delete file even if they were not deleted at the source
    manually_deleted = models.BooleanField(default=False)

    # Store these values for we might need them for a proxy
    oparl_access_url = models.CharField(max_length=512, null=True, blank=True)
    oparl_download_url = models.CharField(max_length=512, null=True, blank=True)

    def __str__(self):
        return self.filename or self.name

    def coordinates(self) -> List[Dict[str, Any]]:
        coordinates = []
        for location in self.locations.all():
            coordinate = location.coordinates()
            if coordinate:
                coordinates.append(coordinate)

        return coordinates

    def person_ids(self):
        return [person.id for person in self.mentioned_persons.all()]

    def get_default_link(self):
        return reverse("file", args=[self.id])

    def name_autocomplete(self):
        return self.name if len(self.name) > 0 else " "

    def get_oparl_url(self) -> Optional[str]:
        return self.oparl_download_url or self.oparl_access_url

    def manually_delete(self):
        """Sometimes we need to delete files even if they were not deleted at the source"""
        self.deleted = True
        self.manually_deleted = True
        self.save()
        minio_client().remove_object(minio_file_bucket, str(self.id))

    def get_assigned_meetings(self):
        from .meeting import Meeting

        return (
            self.meeting_auxiliary_files.all()
            | self.meeting_invitation.all()
            | self.meeting_auxiliary_files.all()
            | self.meeting_results_protocol.all()
            | self.meeting_verbatim_protocol.all()
            | Meeting.objects.filter(agendaitem__resolution_file=self)
        ).distinct()
