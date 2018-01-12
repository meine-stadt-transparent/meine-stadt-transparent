from django_elasticsearch_dsl import DocType, GeoPointField, NestedField, StringField, IntegerField, \
    BooleanField, DateField

from mainapp.models import Meeting
from .utils import mainIndex


@mainIndex.doc_type
class MeetingDocument(DocType):
    location = GeoPointField()
    sort_date = DateField()

    agenda_items = NestedField(attr="agendaitem_set", properties={
        "key": StringField(),
        "title": StringField(),
        "position": IntegerField(),
        "public": BooleanField(),
    })

    @staticmethod
    def prepare_location(instance: Meeting):
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
            'modified',
        ]
