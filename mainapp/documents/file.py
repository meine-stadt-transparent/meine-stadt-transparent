from django_elasticsearch_dsl import DocType, GeoPointField

from mainapp.models import File


# @fileIndex.doc_type
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
