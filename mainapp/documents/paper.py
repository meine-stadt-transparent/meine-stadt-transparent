from django_elasticsearch_dsl import DocType, StringField, IntegerField

from mainapp.models.paper import Paper
from .index import autocomplete_analyzer, elastic_index


@elastic_index.doc_type
class PaperDocument(DocType):
    autocomplete = StringField(attr="get_autocomplete", analyzer=autocomplete_analyzer)
    main_file = IntegerField(attr="main_file_id")
    person_ids = IntegerField(attr="person_ids")
    organization_ids = IntegerField(attr="organization_ids")

    def get_queryset(self):
        return Paper.objects.prefetch_related('persons').prefetch_related('organizations').order_by('id')

    class Meta:
        model = Paper
        queryset_pagination = 500

        fields = [
            "id",
            "short_name",
            "legal_date",
            "created",
            "name",
            "modified",
            "sort_date",
        ]
