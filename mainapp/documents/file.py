from django_elasticsearch_dsl import DocType, GeoPointField, IntegerField, StringField

from mainapp.documents.index import elastic_index, autocomplete_analyzer, text_analyzer
from mainapp.models import File


@elastic_index.doc_type
class FileDocument(DocType):
    autocomplete = StringField(attr="name_autocomplete", analyzer=autocomplete_analyzer)
    coordinates = GeoPointField(attr="coordinates")
    person_ids = IntegerField(attr="person_ids")
    description = StringField(attr="description", analyzer=text_analyzer)
    parsed_text = StringField(attr="parsed_text", analyzer=text_analyzer)

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
            "displayed_filename",
            "page_count",
            "created",
            "modified",
            "sort_date",
        ]
