from django.conf import settings
from django_elasticsearch_dsl import Document, TextField, IntegerField
from django_elasticsearch_dsl.registries import registry

from mainapp.models.paper import Paper
from .index import autocomplete_analyzer


@registry.register_document
class PaperDocument(Document):
    autocomplete = TextField(attr="get_autocomplete", analyzer=autocomplete_analyzer)
    main_file = IntegerField(attr="main_file_id")
    person_ids = IntegerField(attr="person_ids")
    organization_ids = IntegerField(attr="organization_ids")

    def get_queryset(self):
        return (
            Paper.objects.prefetch_related("persons")
            .prefetch_related("organizations")
            .order_by("id")
        )

    class Index:
        name = settings.ELASTICSEARCH_PREFIX + "-paper"

    class Django:
        model = Paper
        queryset_pagination = settings.ELASTICSEARCH_QUERYSET_PAGINATION

        fields = [
            "id",
            "short_name",
            "legal_date",
            "created",
            "name",
            "reference_number",
            "modified",
            "sort_date",
            "display_date",
        ]
