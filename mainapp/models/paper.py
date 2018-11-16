from django.db import models
from django.urls import reverse

from .default_fields import DefaultFields, ShortableNameFields
from .file import File
from .organization import Organization
from .paper_type import PaperType
from .person import Person


class Paper(DefaultFields, ShortableNameFields):
    reference_number = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    organizations = models.ManyToManyField(Organization, blank=True)
    # Only relevant if a person acts independently from one of the submitting organizations
    persons = models.ManyToManyField(Person, blank=True)
    # There isn't any logic built on change requests, so higher order change requests are allowed
    change_request_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE)
    # This is relevant e.g. for deadlines
    legal_date = models.DateField(null=True, blank=True)
    sort_date = models.DateTimeField(auto_now_add=True)
    main_file = models.ForeignKey(File, null=True, blank=True, related_name="paper_main_file", on_delete=models.CASCADE)
    files = models.ManyToManyField(File, blank=True)
    paper_type = models.ForeignKey(PaperType, null=True, blank=True, on_delete=models.CASCADE)

    def get_autocomplete(self):
        autocomplete = self.name + " " + self.reference_number
        return autocomplete if len(autocomplete) > 0 else ' '

    def __str__(self):
        return self.short_name

    def get_default_link(self):
        return reverse('paper', args=[self.id])

    def person_ids(self):
        """ This is actually efficient due to the prefetch """
        return [person.id for person in self.persons.all()]

    def organization_ids(self):
        return [organization.id for organization in self.organizations.all()]

    class Meta:
        # This makes the index page a good bit faster since it uses order_by("-sort_date", "-legal_date")
        indexes = [
            models.Index(fields=['sort_date', 'legal_date']),
        ]
