from django_elasticsearch_dsl import DocType, StringField, IntegerField

from mainapp.models import Person
from .utils import mainIndex, autocomplete_analyzer


@mainIndex.doc_type
class PersonDocument(DocType):
    autocomplete = StringField(attr="name_autocomplete", analyzer=autocomplete_analyzer)
    organization_ids = IntegerField(attr="organization_ids")

    class Meta:
        model = Person

        fields = ['id', 'name', 'given_name', 'family_name',]
