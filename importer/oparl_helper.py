import hashlib
import json
import logging
import os
from datetime import date, datetime
from typing import Optional, Type

import gi
from django.conf import settings
from django.utils import dateparse

from mainapp.functions.document_parsing import extract_text_from_pdf, get_page_count_from_pdf
from mainapp.models import DefaultFields, File
from mainapp.models.default_fields import ShortableNameFields

gi.require_version('OParl', '0.2')
gi.require_version('Json', '1.0')
from gi.repository import Json, GLib, OParl

# You can use those as defaults to inialize the importer. Or inline them when you're already here
# Note that paths are relative to the project root
default_options = {
    "download_files": False,
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

    @staticmethod
    def set_names(libobject: OParl.Object, dbitem: ShortableNameFields, name_fixup=None):
        dbitem.name = libobject.get_name() or name_fixup
        dbitem.set_short_name(libobject.get_short_name() or dbitem.name)
        return dbitem

    # It seems that pycharm doesn't understand generics as in https://github.com/python/typing/issues/107
    # TODO: Check the pycharm bug tracker for that
    def check_existing(self, libobject: OParl.Object, constructor: Type[DefaultFields], add_names=True,
                       name_fixup=None):
        """ Checks common criterias for oparl objects. """
        if not libobject:
            return None

        dbobject = constructor.objects_with_deleted.filter(oparl_id=libobject.get_id()).first()  # type: DefaultFields
        if not dbobject:
            if libobject.get_deleted():
                return None
            self.logger.debug("New")
            dbobject = constructor()
            dbobject.oparl_id = libobject.get_id()
            dbobject.deleted = libobject.get_deleted()
            if add_names:
                self.set_names(libobject, dbobject, name_fixup)
            return dbobject

        if libobject.get_deleted():
            dbobject.deleted = True
            dbobject.save()
            self.logger.debug("Deleted")
            return False

        if not libobject.get_modified():
            error_message = "Modified missing on {}".format(libobject.get_id())
            self.errorlist.append(error_message)
        if not self.ignore_modified and libobject.get_modified() and dbobject.modified > self.glib_datetime_to_python(
                libobject.get_modified()):
            self.logger.debug("Not Modified")
            return None

        self.logger.debug("Modified")
        dbobject.oparl_id = libobject.get_id()
        dbobject.deleted = libobject.get_deleted()
        if add_names:
            self.set_names(libobject, dbobject, name_fixup)
        return dbobject

    def extract_text_from_file(self, file: File):
        path = os.path.join(self.storagefolder, file.storage_filename)
        if file.mime_type == "application/pdf":
            self.logger.info("Extracting text from PDF: " + path)
            try:
                file.parsed_text = extract_text_from_pdf(path)
                file.page_count = get_page_count_from_pdf(path)
            except Exception:
                message = "Could not parse pdf file {}".format(path)
                self.errorlist.append(message)
        elif file.mime_type == "text/text":
            with open(path) as f:
                file.parsed_text = f.read()
