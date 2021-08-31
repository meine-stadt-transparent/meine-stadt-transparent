from typing import Optional, TYPE_CHECKING, Type

from django.db import models

if TYPE_CHECKING:
    from mainapp.models import AgendaItem
from .helper import DefaultFields, DummyInterface, T
from .meeting import Meeting
from .organization import Organization
from .paper import Paper


class Consultation(DefaultFields, DummyInterface):
    """
    See https://github.com/OParl/spec/issues/381 for why we need an extra consultation when there is agenda item
    """

    meeting = models.ForeignKey(
        Meeting, null=True, blank=True, on_delete=models.CASCADE
    )
    paper = models.ForeignKey(Paper, null=True, blank=True, on_delete=models.CASCADE)
    authoritative = models.BooleanField(null=True, blank=True)
    organizations = models.ManyToManyField(Organization, blank=True)
    role = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return "{} {} {}".format(
            self.meeting, self.meeting.id if self.meeting else None, self.paper
        )

    def single_agenda_item(self) -> Optional["AgendaItem"]:
        if self.agendaitem_set.count() == 1:
            return self.agendaitem_set.first()

    @classmethod
    def dummy(cls: Type[T], oparl_id: str) -> T:
        return Consultation(oparl_id=oparl_id)
