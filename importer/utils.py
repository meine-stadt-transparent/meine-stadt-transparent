import logging
import re
from datetime import date, datetime
from importlib import import_module
from typing import Optional

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

logger = logging.getLogger(__name__)


class Utils:
    """A collection of helper function for the oparl importer.

    These are methods and not functions so they can be easily overwritten.
    """

    def __init__(self):
        self.official_geojson = True
        self.filename_length_cutoff = 100
        self.organization_classification = {
            "Fraktion": settings.PARLIAMENTARY_GROUPS_TYPE[0],
            "Fraktionen": settings.PARLIAMENTARY_GROUPS_TYPE[0],
            "Stadtratsgremium": settings.COMMITTEE_TYPE[0],
            "BA-Gremium": settings.COMMITTEE_TYPE[0],
            "Gremien": settings.COMMITTEE_TYPE[0],
            "Gremium": settings.COMMITTEE_TYPE[0],
            "Referat": settings.DEPARTMENT_TYPE[0],
        }

        if settings.CUSTOM_IMPORT_HOOKS:
            self.custom_hooks = import_module(settings.CUSTOM_IMPORT_HOOKS)
        else:
            self.custom_hooks = None

        self.start = timezone.now().astimezone().replace(microsecond=0)

    def call_custom_hook(self, hook_name: str, hook_parameter):
        if self.custom_hooks and hasattr(self.custom_hooks, hook_name):
            return getattr(self.custom_hooks, hook_name)(hook_parameter)
        else:
            return hook_parameter

    def parse_date(self, data: Optional[str]) -> Optional[date]:
        if not data:
            return None
        return parse_date(data)

    def parse_datetime(self, data: Optional[str]) -> Optional[datetime]:
        if not data:
            return None
        return parse_datetime(data)

    def date_to_datetime(self, data: Optional[date]) -> Optional[datetime]:
        if not data:
            return None

        current_timezone = timezone.now().astimezone().tzinfo
        date_as_datime = datetime.combine(data, datetime.min.time())
        return date_as_datime.replace(tzinfo=current_timezone)

    def normalize_body_name(self, short_name: str) -> str:
        """Cuts away e.g. "Stadt" from "Stadt Leipzig" and normalizes the spaces"""
        for affix in settings.CITY_AFFIXES:
            short_name = short_name.replace(affix, "")
        return re.sub(" +", " ", short_name).strip()
