from django_elasticsearch_dsl import DocType, GeoPointField

from mainapp.documents.utils import mainIndex
from mainapp.models import File


@mainIndex.doc_type
class FileDocument(DocType):
    coordinates = GeoPointField(attr="coordinates")

    class Meta:
        model = File

        fields = [
            'id',
            'name',
            'description',
            'displayed_filename',
            'created',
        ]
