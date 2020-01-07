from django.conf import settings
from django.db.models import Prefetch
from django_elasticsearch_dsl import Document, TextField, IntegerField, DateField
from django_elasticsearch_dsl.registries import registry

from mainapp.models import Person, Membership
from .index import autocomplete_analyzer


@registry.register_document
class PersonDocument(Document):
    autocomplete = TextField(attr="name_autocomplete", analyzer=autocomplete_analyzer)
    sort_date = DateField()
    organization_ids = IntegerField(attr="organization_ids")

    def get_queryset(self):
        sort_date_queryset = Membership.objects.filter(start__isnull=False).order_by(
            "-start"
        )

        return (
            Person.objects.order_by("id")
            .prefetch_related("membership_set")
            .prefetch_related(
                Prefetch(
                    "membership_set",
                    queryset=sort_date_queryset,
                    to_attr="sort_date_prefetch",
                )
            )
        )

    class Index:
        name = settings.ELASTICSEARCH_PREFIX + "-person"

    class Django:
        model = Person
        queryset_pagination = settings.ELASTICSEARCH_QUERYSET_PAGINATION

        fields = ["id", "name", "given_name", "family_name"]
