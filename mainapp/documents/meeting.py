from typing import Optional, Dict, Any

from django_elasticsearch_dsl import (
    DocType,
    GeoPointField,
    NestedField,
    TextField,
    IntegerField,
    BooleanField,
    DateField,
)

from mainapp.documents.index import elastic_index_meeting
from mainapp.models import Meeting
from .index import text_analyzer


@elastic_index_meeting.doc_type
class MeetingDocument(DocType):
    location = GeoPointField()
    sort_date = DateField()

    agenda_items = NestedField(
        attr="agendaitem_set",
        properties={
            "key": TextField(),
            "name": TextField(analyzer=text_analyzer),
            "position": IntegerField(),
            "public": BooleanField(),
        },
    )

    @staticmethod
    def prepare_location(instance: Meeting) -> Optional[Dict[str, Any]]:
        if instance.location:
            return instance.location.coordinates()

    def get_queryset(self):
        return (
            Meeting.objects.prefetch_related("agendaitem_set")
            .prefetch_related("location")
            .order_by("id")
        )

    class Meta:
        model = Meeting
        queryset_pagination = 500

        fields = ["id", "name", "short_name", "start", "end", "created", "modified"]
