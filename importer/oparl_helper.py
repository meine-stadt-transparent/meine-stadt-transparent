import hashlib
import json
import logging
import os
from datetime import date, datetime
from importlib import import_module
from typing import Optional, Type, Tuple, TypeVar, Callable

import gi
from django.conf import settings
from django.utils import dateparse

from mainapp.functions.document_parsing import extract_text_from_pdf, get_page_count_from_pdf
from mainapp.models import DefaultFields, File
from mainapp.models.default_fields import ShortableNameFields

gi.require_version('OParl', '0.4')
gi.require_version('Json', '1.0')
from gi.repository import Json, GLib, OParl

# You can use those as defaults to inialize the importer. Or inline them when you're already here
# Note that paths are relative to the project root
default_options = {
    "download_files": True,
    "use_cache": True,
    "use_sternberg": False,
    "ignore_modified": False,
    "no_threads": False,
    "cachefolder": settings.CACHE_ROOT,
    "storagefolder": settings.MEDIA_ROOT,
    "batchsize": 100,
    "threadcount": 10,
}


class OParlHelper:
    """ A collection of helper function for the oparl importer.

    These are methods and not functions so they can be easily overwritten.
    """

    def __init__(self, options):
        self.ignore_modified = options["ignore_modified"]
        self.storagefolder = options["storagefolder"]
        self.entrypoint = options["entrypoint"]
        self.use_cache = options["use_cache"]
        self.download_files = options["download_files"]
        self.threadcount = options["threadcount"]
        self.batchsize = options["batchsize"]
        self.no_threads = options["no_threads"]
        entrypoint_hash = hashlib.sha1(self.entrypoint.encode("utf-8")).hexdigest()
        self.cachefolder = os.path.join(options["cachefolder"], entrypoint_hash)
        self.download_files = options["download_files"]
        self.official_geojson = False
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

        self.errorlist = []
        self.logger = logging.getLogger(__name__)

        if settings.CUSTOM_IMPORT_HOOKS:
            self.custom_hooks = import_module(settings.CUSTOM_IMPORT_HOOKS)
        else:
            self.custom_hooks = None

    @staticmethod
    def extract_geometry(glib_json: Json.Object):
        """ Extracts the geometry part of the geojson as python object. A bit ugly. """
        if not glib_json:
            return None
        node = glib_json.get_member('geometry')
        return json.loads(Json.to_string(node, True))

    @staticmethod
    def glib_datetime_to_python(glibdatetime: GLib.DateTime) -> Optional[datetime]:
        if not glibdatetime:
            return None
        return dateparse.parse_datetime(glibdatetime.format("%FT%T%z"))

    @staticmethod
    def glib_datetime_to_python_date(glibdatetime: GLib.DateTime) -> Optional[date]:
        # TODO: Remove once https://github.com/OParl/liboparl/issues/18 is fixed
        if not glibdatetime:
            return None
        return date(glibdatetime.get_year(), glibdatetime.get_month(), glibdatetime.get_day_of_month())

    @staticmethod
    def glib_date_to_python(glibdate: GLib.Date) -> Optional[date]:
        if not glibdate:
            return None
        return date(glibdate.get_year(), glibdate.get_month(), glibdate.get_day())

    @classmethod
    def glib_datetime_or_date_to_python(cls, glibdate: GLib.DateTime):
        if isinstance(glibdate, GLib.Date):
            return cls.glib_date_to_python(glibdate)
        if isinstance(glibdate, GLib.DateTime):
            return cls.glib_datetime_to_python_date(glibdate)
        return None

    T = TypeVar("T", bound=DefaultFields)
    U = TypeVar("U", bound=OParl.Object)

    def process_object(self, libobject: U, constructor: Type[T], core: Callable[[U, T], None],
                       embedded: Callable[[U, T], bool]):
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

    # NOTE: Typechecking fails due to https://youtrack.jetbrains.com/issue/PY-23161 (TODO: Wait for that to be fixed)
    def check_for_modification(self, libobject: OParl.Object, constructor: Type[E], name_fixup=None) \
            -> Tuple[Optional[E], bool]:
        """ Checks common criterias for oparl objects. """
        if not libobject:
            return None, False

        oparl_id = libobject.get_id()
        dbobject = constructor.objects_with_deleted.filter(oparl_id=oparl_id).first()  # type: DefaultFields
        if not dbobject:
            if libobject.get_deleted():
                # This was deleted before it could be imported, so we skip it
                return None, False
            self.logger.debug("New %s", oparl_id)
            dbobject = constructor()
            dbobject.oparl_id = oparl_id
            dbobject.deleted = libobject.get_deleted()
            if isinstance(dbobject, ShortableNameFields):
                dbobject.name = libobject.get_name() or name_fixup
                dbobject.set_short_name(libobject.get_short_name() or dbobject.name)
            return dbobject, True

        if libobject.get_deleted():
            dbobject.deleted = True
            dbobject.save()
            self.logger.debug("Deleted %s: %s", dbobject.id, oparl_id)
            return dbobject, False

        parsed_modified = self.glib_datetime_to_python(libobject.get_modified())
        if self.ignore_modified:
            is_modified = True
        elif not libobject.get_modified():
            self.logger.debug("No modified on {}".format(oparl_id))
            is_modified = True
        elif dbobject.modified > parsed_modified:
            is_modified = False
        else:
            is_modified = True

        if is_modified:
            self.logger.debug("Modified %s vs. %s on %s: %s", dbobject.modified, parsed_modified, dbobject.id, oparl_id)
            if isinstance(dbobject, ShortableNameFields):
                dbobject.name = libobject.get_name() or name_fixup
                dbobject.set_short_name(libobject.get_short_name() or dbobject.name)
            return dbobject, True
        else:
            self.logger.debug("Not Modified %s vs. %s on %s: %s", dbobject.modified, parsed_modified, dbobject.id,
                              oparl_id)
            return dbobject, False

    def extract_text_from_file(self, file: File):
        path = os.path.join(self.storagefolder, file.storage_filename)
        parsed_text = None
        if file.mime_type == "application/pdf":
            self.logger.info("Extracting text from PDF: " + path)
            try:
                parsed_text = extract_text_from_pdf(path)
                file.page_count = get_page_count_from_pdf(path)
            except Exception:
                message = "Could not parse pdf file {}".format(path)
                self.logger.error(message)
                self.errorlist.append(message)
        elif file.mime_type == "text/text":
            with open(path) as f:
                parsed_text = f.read()
        file.parsed_text = parsed_text
        return parsed_text

    @staticmethod
    def is_queryset_equal_list(queryset, other):
        """ Sufficiently correct comparison of a querysets and a list, inspired by django's assertQuerysetEqual """
        return list(queryset.order_by("id").all()) == sorted(other, key=id)

    def call_custom_hook(self, hook_name, hook_parameter):
        if self.custom_hooks and hasattr(self.custom_hooks, hook_name):
            return getattr(self.custom_hooks, hook_name)(hook_parameter)
        else:
            return hook_parameter
