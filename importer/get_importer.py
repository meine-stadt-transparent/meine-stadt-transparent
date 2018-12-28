import re
from datetime import date, datetime
from django.utils.dateparse import parse_datetime, parse_date
from typing import Dict, Any, TYPE_CHECKING, Optional

import requests
from django.conf import settings

from mainapp.models import Body

if TYPE_CHECKING:
    from importer.oparl_import import OParlImport


def parse_date_opt(data: Optional[str]) -> Optional[date]:
    if not data:
        return None
    return parse_date(data)


def parse_datetime_opt(data: Optional[str]) -> Optional[datetime]:
    if not data:
        return None
    return parse_datetime(data)


def get_importer(options: Dict[str, Any]) -> "OParlImport":
    """ Queries the system object to determine the vendor and the necessary workarounds. """

    from importer.oparl_import import OParlImport
    from importer.sternberg_import import SternbergImport

    response = requests.get(options["entrypoint"])
    response.raise_for_status()
    system = response.json()

    # This will likely need a more sophisticated logic in te future
    if system.get("contactName") == "STERNBERG Software GmbH & Co. KG":
        return SternbergImport(options)
    else:
        return OParlImport(options)


def normalize_body_name(body: Body) -> None:
    """ Cuts away e.g. "Stadt" from "Stadt Leipzig" and normalizes the spaces """
    name = body.short_name
    for affix in settings.CITY_AFFIXES:
        name = name.replace(affix, "")
    name = re.sub(" +", " ", name).strip()
    body.short_name = name
