from django_elasticsearch_dsl import DocType, StringField, IntegerField

from mainapp.models.paper import Paper
from .utils import autocomplete_analyzer, mainIndex


@mainIndex.doc_type
class PaperDocument(DocType):
    # FIXME: Name should also autocomplete. Maybe add an extra negative bias
    # autocomplete_name = StringField(attr="name", analyzer=autocomplete_analyzer)
    autocomplete = StringField(attr="reference_number_autocomplete", analyzer=autocomplete_analyzer)
    main_file = IntegerField(attr="main_file_id")
    person_ids = IntegerField(attr="person_ids")

    class Meta:
        model = Paper

        fields = [
            'id',
            'name',
            'short_name',
            'description',
            'legal_date',
            'created',
            'modified',
        ]
