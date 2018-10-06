from typing import Optional, Dict, Any

from django_elasticsearch_dsl import (
    DocType,
    GeoPointField,
    NestedField,
    StringField,
    IntegerField,
    BooleanField,
    DateField,
)

from mainapp.models import Meeting
from .index import elastic_index, text_analyzer


@elastic_index.doc_type
class MeetingDocument(DocType):
    location = GeoPointField()
    sort_date = DateField()

    agenda_items = NestedField(
        attr="agendaitem_set",
        properties={
            "key": StringField(),
            "title": StringField(analyzer=text_analyzer),
            "position": IntegerField(),
            "public": BooleanField(),
        },
    )

    @staticmethod
    def prepare_location(instance: Meeting) -> Optional[Dict[str, Any]]:
        if instance.location:
            return instance.location.coordinates()

    def get_queryset(self):
        return Meeting.objects.prefetch_related("agendaitem_set").prefetch_related("location").order_by('id')

    class Meta:
        model = Meeting
        queryset_pagination = 500

        fields = ["id", "name", "short_name", "start", "end", "created", "modified"]
