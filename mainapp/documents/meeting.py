from typing import Optional, Dict, Any

from django.conf import settings
from django_elasticsearch_dsl import (
    Document,
    GeoPointField,
    NestedField,
    TextField,
    IntegerField,
    BooleanField,
    DateField,
)
from django_elasticsearch_dsl.registries import registry

from mainapp.models import Meeting
from .index import text_analyzer


@registry.register_document
class MeetingDocument(Document):
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

    class Index:
        name = settings.ELASTICSEARCH_PREFIX + "-meeting"

    class Django:
        model = Meeting
        queryset_pagination = settings.ELASTICSEARCH_QUERYSET_PAGINATION

        fields = ["id", "name", "short_name", "start", "end", "created", "modified"]
