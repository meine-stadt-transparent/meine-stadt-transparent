import json
import logging
import re
from collections import namedtuple
from datetime import date, datetime
from importlib import import_module
from io import BytesIO
from tempfile import NamedTemporaryFile
from typing import Dict, Any, Tuple
from typing import Optional
from typing import Type, TypeVar, Callable

import requests
from django.conf import settings
from django.utils.dateparse import parse_date, parse_datetime
from minio.error import NoSuchKey
from requests import HTTPError

from mainapp.functions.document_parsing import (
    extract_text_from_pdf,
    get_page_count_from_pdf,
)
from mainapp.functions.minio import minio_client, minio_cache_bucket
from mainapp.functions.minio import minio_file_bucket
from mainapp.models import DefaultFields, File, Body
from mainapp.models.default_fields import ShortableNameFields

logger = logging.getLogger(__name__)

ResolveUrlResult = namedtuple("ResolveUrlResult", "resolved_data success status_code")

# You can use those as defaults to inialize the importer. Or inline them when you're already here
# Note that paths are relative to the project root
default_options = {
    "download_files": True,
    "use_cache": True,
    "ignore_modified": False,
    "no_threads": True,
    "threadcount": 10,
    "entrypoint": settings.OPARL_ENDPOINT,
}


class OParlUtils:
    """ A collection of helper function for the oparl importer.

    These are methods and not functions so they can be easily overwritten.
    """

    def __init__(self, options: Dict[str, Any]):
        self.ignore_modified = options["ignore_modified"]
        self.entrypoint = options["entrypoint"]
        self.use_cache = options["use_cache"]
        self.download_files = options["download_files"]
        self.threadcount = options["threadcount"]
        self.no_threads = options["no_threads"]
        self.download_files = options["download_files"]
        self.minio_client = minio_client
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

        self.logger = logging.getLogger(__name__)

        if settings.CUSTOM_IMPORT_HOOKS:
            self.custom_hooks = import_module(settings.CUSTOM_IMPORT_HOOKS)
        else:
            self.custom_hooks = None

    def resolve(self, url: str) -> ResolveUrlResult:
        if self.use_cache:
            try:
                data = self.minio_client.get_object(
                    minio_cache_bucket, url + "-disambiguate-file"
                )
                data = json.load(data)
                self.logger.info("Cached: " + url)
                return ResolveUrlResult(
                    resolved_data=data, success=True, status_code=304
                )
            except NoSuchKey:
                pass

        try:
            self.logger.info("Loading: " + url)
            req = requests.get(url)
        except Exception as e:
            self.logger.error("Error loading url: ", e)
            return ResolveUrlResult(resolved_data=None, success=False, status_code=-1)

        content = req.content
        data = json.loads(content.decode())

        try:
            req.raise_for_status()
        except Exception as e:
            self.logger.error("HTTP status code error: ", e)
            return ResolveUrlResult(
                resolved_data=data, success=False, status_code=req.status_code
            )

        # We need to avoid filenames where a prefix already is a file, which fails with a weird minio error
        self.minio_client.put_object(
            minio_cache_bucket,
            url + "-disambiguate-file",
            BytesIO(content),
            len(content),
        )

        return ResolveUrlResult(
            resolved_data=data, success=True, status_code=req.status_code
        )

    T = TypeVar("T", bound=DefaultFields)
    U = TypeVar("U", bound=Dict[str, Any])

    def process_object(
        self,
        libobject: U,
        constructor: Type[T],
        core: Callable[[U, T], None],
        embedded: Callable[[U, T], bool],
    ) -> T:
        """
        We split an object into two parts: It's value properties and the embedded objects. This is necessary because
        the outer object might not have been modified while its embedded inner objects have.
        """
        outer_object, do_update = self.check_for_modification(libobject, constructor)
        if do_update:
            core(libobject, outer_object)
            outer_object.save()
        if outer_object:
            associates_changed = embedded(libobject, outer_object)
            if associates_changed:
                outer_object.save()

        return outer_object

    E = TypeVar("E", bound=DefaultFields)

    def check_for_modification(
        self,
        libobject: Optional[Dict[str, Any]],
        constructor: Type[E],
        name_fixup: Optional[str] = None,
    ) -> Tuple[Optional[E], bool]:
        """ Checks common criteria for oparl objects. """
        if not libobject:
            return None, False

        dbobject = constructor.objects_with_deleted.filter(
            oparl_id=libobject["id"]
        ).first()  # type: DefaultFields
        if not dbobject:
            if libobject.get("deleted"):
                # This was deleted before it could be imported, so we skip it
                return None, False
            self.logger.debug("New %s", libobject["id"])
            dbobject = constructor()
            dbobject.oparl_id = libobject["id"]
            dbobject.deleted = bool(libobject.get("deleted"))
            if isinstance(dbobject, ShortableNameFields):
                dbobject.name = libobject.get("name") or name_fixup
                dbobject.set_short_name(libobject.get("shortName") or dbobject.name)
            return dbobject, True

        return self._check_for_modification(dbobject, libobject, name_fixup)

    def _check_for_modification(
        self, dbobject: E, libobject: Dict[str, Any], name_fixup: Optional[str]
    ) -> Tuple[Optional[E], bool]:
        if libobject.get("deleted"):
            dbobject.deleted = True
            dbobject.save()
            self.logger.debug("Deleted {}: {}".format(dbobject, libobject["id"]))
            return dbobject, False

        modified = self.parse_datetime(libobject.get("modified"))
        is_modified = (not modified) or dbobject.modified < modified

        if is_modified and not self.ignore_modified:
            self.logger.debug(
                "Modified %s vs. %s on %s: %s",
                dbobject.modified,
                modified,
                dbobject.id,
                libobject["id"],
            )
            if isinstance(dbobject, ShortableNameFields):
                dbobject.name = libobject.get("name") or name_fixup
                dbobject.set_short_name(libobject.get("shortName") or dbobject.name)
        else:
            self.logger.debug(
                "Not Modified %s vs. %s on %s: %s",
                dbobject.modified,
                modified,
                dbobject.id,
                libobject["id"],
            )
        return dbobject, is_modified

    def extract_text_from_file(self, file: File, path: str) -> Optional[str]:
        parsed_text = None
        if file.mime_type == "application/pdf":
            self.logger.info(
                "Extracting text from PDF for file {} ({})".format(file.id, file)
            )
            try:
                parsed_text = extract_text_from_pdf(path)
                file.page_count = get_page_count_from_pdf(path)
            except Exception as e:
                message = "Could not parse pdf for file {}: {}".format(file.id, e)
                self.logger.exception(message)
        elif file.mime_type == "text/text":
            with open(path) as f:
                parsed_text = f.read()
        return parsed_text

    def is_queryset_equal_list(self, queryset, other) -> bool:
        """ Sufficiently correct comparison of a querysets and a list, inspired by django's assertQuerysetEqual """
        return list(queryset.order_by("id").all()) == sorted(other, key=id)

    def call_custom_hook(self, hook_name, hook_parameter):
        if self.custom_hooks and hasattr(self.custom_hooks, hook_name):
            return getattr(self.custom_hooks, hook_name)(hook_parameter)
        else:
            return hook_parameter

    def download_file(
        self, file: File, url: str, libobject: Dict[str, Any]
    ) -> Optional[NamedTemporaryFile]:
        last_modified = self.parse_datetime(libobject.get("modified"))

        if (
            file.filesize > 0
            and last_modified
            and last_modified < file.modified
            and minio_client.has_object(minio_file_bucket, str(file.id))
        ):
            logger.info("Skipping cached download: {}".format(url))
            return

        logger.info("Downloading {}".format(url))

        response = requests.get(url, allow_redirects=True)

        try:
            response.raise_for_status()
        except HTTPError as e:
            logger.exception("Failed to download file {}: {}", file.id, e)
            return

        tmpfile = NamedTemporaryFile()
        content = response.content
        tmpfile.write(content)
        tmpfile.file.seek(0)
        file.filesize = len(content)

        minio_client.put_object(
            minio_file_bucket,
            str(file.id),
            tmpfile.file,
            file.filesize,
            content_type=file.mime_type,
        )
        return tmpfile

    def parse_date(self, data: Optional[str]) -> Optional[date]:
        if not data:
            return None
        return parse_date(data)

    def parse_datetime(self, data: Optional[str]) -> Optional[datetime]:
        if not data:
            return None
        return parse_datetime(data)

    def normalize_body_name(self, body: Body) -> None:
        """ Cuts away e.g. "Stadt" from "Stadt Leipzig" and normalizes the spaces """
        name = body.short_name
        for affix in settings.CITY_AFFIXES:
            name = name.replace(affix, "")
        name = re.sub(" +", " ", name).strip()
        body.short_name = name
