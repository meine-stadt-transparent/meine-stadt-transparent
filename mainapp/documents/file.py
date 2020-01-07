from django.conf import settings
from django_elasticsearch_dsl import Document, GeoPointField, IntegerField, TextField
from django_elasticsearch_dsl.registries import registry

from mainapp.documents.index import autocomplete_analyzer, text_analyzer
from mainapp.models import File


@registry.register_document
class FileDocument(Document):
    autocomplete = TextField(attr="name_autocomplete", analyzer=autocomplete_analyzer)
    coordinates = GeoPointField(attr="coordinates")
    person_ids = IntegerField(attr="person_ids")
    description = TextField(attr="description", analyzer=text_analyzer)
    # Elasticsearch wants `index_options: "offsets"` for the highlighter for large texts
    parsed_text = TextField(
        attr="parsed_text", analyzer=text_analyzer, index_options="offsets"
    )

    def get_queryset(self):
        return (
            File.objects.prefetch_related("locations")
            .prefetch_related("mentioned_persons")
            .order_by("id")
        )

    class Index:
        name = settings.ELASTICSEARCH_PREFIX + "-file"

    class Django:
        model = File
        queryset_pagination = settings.ELASTICSEARCH_QUERYSET_PAGINATION

        fields = [
            "id",
            "name",
            "filename",
            "page_count",
            "created",
            "modified",
            "sort_date",
        ]
