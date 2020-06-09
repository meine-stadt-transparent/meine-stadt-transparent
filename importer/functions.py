import datetime
import logging
from typing import Optional, Set, List, Type

import requests
from django.db.models import OuterRef, Q, Subquery, F
from slugify import slugify

from importer import JSON
from importer.models import CachedObject, ExternalList
from mainapp.functions.search import search_bulk_index
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
from mainapp.models.file import fallback_date
from meine_stadt_transparent import settings

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


def requests_get(url, params=None, **kwargs) -> requests.Response:
    """ Makes a request with the custom user agent """
    user_agent = "{} ({})".format(
        slugify(settings.PRODUCT_NAME), settings.TEMPLATE_META["github"]
    )
    kwargs.setdefault("headers", {})
    kwargs["headers"]["User-Agent"] = user_agent
    response = requests.get(url, params, **kwargs)
    response.raise_for_status()
    return response


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
    from importer.loader import get_loader_from_body

    if body_id:
        bodies = Body.objects.filter(oparl_id=body_id).all()
    else:
        bodies = Body.objects.filter(oparl_id__isnull=False).all()
    for body in bodies:
        logger.info("Updating body {}: {}".format(body, body.oparl_id))
        loader = get_loader_from_body(body.oparl_id)
        importer = Importer(loader, body, ignore_modified=ignore_modified)
        importer.update(body.oparl_id)
        importer.force_singlethread = True
        importer.load_files(body.short_name)


def fix_sort_date(import_date: datetime.datetime):
    """
    Tries to guess the correct sort date for all papers and files that were created no later
    than import_date by looking at
      a) the legal date,
      b) the the date of the earliest consultation or
      c) falling back to fallback_date
    """
    logger.info("Fixing the sort date of the papers")
    # Use the date of the earliest consultation
    earliest_consultation = (
        Consultation.objects.filter(paper=OuterRef("pk"), meeting__isnull=False)
        .order_by("meeting__start")
        .values("meeting__start")[:1]
    )
    papers_with_consultation = (
        Paper.objects.filter(Q(sort_date=fallback_date) | ~Q(sort_date=F("legal_date")))
        .annotate(earliest_consultation=Subquery(earliest_consultation))
        .filter(earliest_consultation__isnull=False)
        # We filter on these to only update those necessary in elasticsearch
        .filter(
            ~Q(sort_date=F("earliest_consultation"))
            & ~Q(display_date=F("earliest_consultation"))
        )
    )
    num = papers_with_consultation.update(
        sort_date=F("earliest_consultation"), display_date=F("earliest_consultation")
    )
    if settings.ELASTICSEARCH_ENABLED:
        search_bulk_index(Paper, papers_with_consultation)
    logger.info(f"{num} sort dates were fix by the earliest consultation")

    logger.info("Fixing the sort date of the files")
    num = File.objects.filter(
        created__lte=import_date, legal_date__isnull=False
    ).update(sort_date=F("legal_date"), modified=F("legal_date"))
    logger.info(f"{num} files were changed")

    earliest_paper = (
        Paper.objects.filter(files__pk=OuterRef("pk"))
        .order_by("sort_date")
        .values("sort_date")[:1]
    )
    file_with_paper = (
        File.objects.filter(legal_date__isnull=True)
        .annotate(earliest_paper=Subquery(earliest_paper))
        .filter(earliest_paper__isnull=False)
        # We filter on these to only update those necessary in elasticsearch
        .filter(~Q(sort_date=F("earliest_paper")))
    )
    num = file_with_paper.update(sort_date=F("earliest_paper"))
    if settings.ELASTICSEARCH_ENABLED:
        search_bulk_index(Paper, file_with_paper)
    logger.info(f"{num} files updated")
