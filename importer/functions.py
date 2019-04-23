import logging
from typing import Optional, Set, List, Type

from importer import JSON
from importer.loader import get_loader_from_body
from importer.models import CachedObject, ExternalList
from mainapp.models import (
    LegislativeTerm,
    Location,
    Body,
    File,
    Person,
    Organization,
    Membership,
    Meeting,
    Paper,
    Consultation,
    AgendaItem,
    DefaultFields,
)

logger = logging.getLogger(__name__)

import_order = [
    LegislativeTerm,
    Location,
    Body,
    File,
    Person,
    Organization,
    Membership,
    Meeting,
    Paper,
    Consultation,
    AgendaItem,
]  # type: List[Type[DefaultFields]]


def externalize(
    libobject: JSON, key_callback: Optional[Set[str]] = None
) -> List[CachedObject]:
    """ Converts an oparl object with embedded objects to multiple flat json objeczs """

    externalized = []

    for key in libobject.keys():
        # Skip the geojson object
        if key == "geojson":
            continue

        entry = libobject[key]

        if isinstance(entry, dict):
            if isinstance(key_callback, set):
                key_callback.add(key)
            entry["mst:backref"] = libobject["id"]

            externalized += externalize(entry)
            libobject[key] = entry["id"]

        if isinstance(entry, list) and len(entry) > 0 and isinstance(entry[0], dict):
            if isinstance(key_callback, set):
                key_callback.add(key)
            for pos, entry in enumerate(entry):
                entry["mst:backref"] = libobject["id"]
                entry["mst:backrefPosition"] = pos  # We need this for agenda items

                externalized += externalize(entry)
                libobject[key][pos] = entry["id"]

    externalized.append(
        CachedObject(
            url=libobject["id"],
            data=libobject,
            oparl_type=libobject["type"].split("/")[-1],
        )
    )

    return externalized


def clear_import(prefix: str, include_cache: bool = True) -> None:
    """ Clear all data from the oparl api identified by the prefix """
    for class_object in import_order:
        name = class_object.__name__
        stats = class_object.objects.filter(oparl_id__startswith=prefix).delete()
        logger.info("{}: {}".format(name, stats))
    if include_cache:
        logger.info(CachedObject.objects.filter(url__startswith=prefix).delete())
        logger.info(ExternalList.objects.filter(url__startswith=prefix).delete())


def import_update(body_id: Optional[str] = None, ignore_modified: bool = False) -> None:
    from importer.importer import Importer

    if body_id:
        bodies = Body.objects.filter(oparl_id=body_id).all()
    else:
        bodies = Body.objects.filter(oparl_id__isnull=False).all()
    for body in bodies:
        logger.info("Updating body {}: {}".format(body, body.oparl_id))
        loader = get_loader_from_body(body.oparl_id)
        importer = Importer(loader, body, ignore_modified=ignore_modified)
        importer.update(body.oparl_id)
