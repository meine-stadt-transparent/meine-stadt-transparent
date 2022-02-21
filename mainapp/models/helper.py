import re
import textwrap
from abc import abstractmethod
from typing import TypeVar, Type

from django.db import models
from simple_history.models import HistoricalRecords


class SoftDeleteModelManager(models.Manager):
    def get_queryset(self):
        queryset = models.query.QuerySet(self.model, using=self._db)
        return queryset.filter(deleted=0)

    def get_or_create(self, defaults=None, **kwargs):
        raise ValueError(
            "get_or_create with `objects` is bogus, use `objects_with_deleted` instead"
        )

    def update_or_create(self, defaults=None, **kwargs):
        raise ValueError(
            "update_or_create with `objects` is bogus, use `objects_with_deleted` instead"
        )


class SoftDeleteModelManagerWithDeleted(models.Manager):
    def get_queryset(self):
        return models.query.QuerySet(self.model, using=self._db)


class DefaultFields(models.Model):
    """
    These fields are mainly inspired and required by oparl
    """

    oparl_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False, db_index=True)

    objects = SoftDeleteModelManager()
    objects_with_deleted = SoftDeleteModelManagerWithDeleted()

    history = HistoricalRecords(inherit=True)

    @classmethod
    def by_oparl_id(cls, oparl_id):
        return cls.objects.get(oparl_id=oparl_id)

    def save_without_historical_record(self, *args, **kwargs):
        self.skip_history_when_saving = True
        try:
            ret = self.save(*args, **kwargs)
        finally:
            del self.skip_history_when_saving
        return ret

    class Meta:
        abstract = True


class ShortableNameFields(models.Model):
    name = models.TextField()
    short_name = models.CharField(max_length=50)

    def has_alternative_short_name(self):
        """
        Returns True, if short_name (minus the … at the end) is NOT the beginning of name,
        i.e. contains really individual content
        :return: bool
        """
        short_normalized = re.sub(r"\u2026$", "", self.short_name)
        position = self.name.find(short_normalized)
        if position == 0:
            return False
        else:
            return True

    def set_short_name(self, name: str):
        if len(name) > 50:
            name = textwrap.wrap(name, 49)[0] + "\u2026"
        self.short_name = name

    class Meta:
        abstract = True


# noinspection PyTypeChecker
T = TypeVar("T", bound="DummyMixin")  # noqa F821


class DummyInterface:
    @classmethod
    @abstractmethod
    def dummy(cls: Type[T], oparl_id: str) -> T:
        raise NotImplementedError

    class Meta:
        abstract = True
