from django_elasticsearch_dsl import DocType, GeoPointField, IntegerField

from mainapp.documents.utils import mainIndex
from mainapp.models import File


@mainIndex.doc_type
class FileDocument(DocType):
    coordinates = GeoPointField(attr="coordinates")
    person_ids = IntegerField(attr="person_ids")

    class Meta:
        model = File

        fields = [
            'id',
            'name',
            'description',
            'displayed_filename',
            'page_count',
            'parsed_text',
            'created',
            'modified',
        ]
