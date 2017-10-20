from django_elasticsearch_dsl import DocType, fields

from mainapp.models import File


# @fileIndex.doc_type
class FileDocument(DocType):
    coordinates = fields.GeoPointField(attr="coordinates")

    class Meta:
        model = File

        fields = [
            'id',
            'name',
            'description',
            'displayed_filename',
            'created',
        ]
