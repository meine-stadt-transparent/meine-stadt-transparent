from django_elasticsearch_dsl import DocType, fields

from mainapp.models import Meeting
from .utils import fileIndex


@fileIndex.doc_type
class MeetingDocument(DocType):
    location = fields.GeoPointField()
    agenda_items = fields.NestedField(attr="agendaitem_set", properties={
        "key": fields.StringField(),
        "title": fields.StringField(),
        "position": fields.IntegerField(),
        "public": fields.BooleanField(),
    })

    def prepare_location(self, instance: Meeting):
        if instance.location:
            return instance.location.coordinates()

    class Meta:
        model = Meeting

        fields = [
            'id',
            'name',
            'short_name',
            'start',
            'end',
            'created',
        ]
