from django_elasticsearch_dsl import DocType, GeoPointField, IntegerField, TextField

from mainapp.documents.index import (
    autocomplete_analyzer,
    text_analyzer,
    elastic_index_file,
)
from mainapp.models import File


@elastic_index_file.doc_type
class FileDocument(DocType):
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

    class Meta:
        model = File
        queryset_pagination = 500

        fields = [
            "id",
            "name",
            "filename",
            "page_count",
            "created",
            "modified",
            "sort_date",
        ]
