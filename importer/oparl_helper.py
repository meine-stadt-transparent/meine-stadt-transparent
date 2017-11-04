import hashlib
import json
import logging
import os
from datetime import date, datetime
from typing import Optional, Type

import gi
from django.utils import dateparse
from pdfminer.pdfdocument import PDFTextExtractionNotAllowed

from mainapp.functions.document_parsing import extract_text_from_pdf
from mainapp.models import DefaultFields, File
from mainapp.models import Department, Committee, ParliamentaryGroup

gi.require_version('OParl', '0.2')
gi.require_version('Json', '1.0')
from gi.repository import Json, GLib, OParl


class OParlHelper:
    """ A collection of helper function for the oparl importer.

    These are methods and not functions so they can be easily overwritten.
    """

    def __init__(self, options):
        self.storagefolder = options["storagefolder"]
        self.entrypoint = options["entrypoint"]
        self.use_cache = options["use_cache"]
        self.download_files = options["download_files"]
        self.with_persons = options["with_persons"]
        self.with_papers = options["with_papers"]
        self.with_organizations = options["with_organizations"]
        self.with_meetings = options["with_meetings"]
        self.threadcount = options["threadcount"]
        self.batchsize = options["batchsize"]
        self.no_threads = options["no_threads"]
        entrypoint_hash = hashlib.sha1(self.entrypoint.encode("utf-8")).hexdigest()
        self.cachefolder = os.path.join(options["cachefolder"], entrypoint_hash)
        self.download_files = options["download_files"]
        self.official_geojson = False
        self.filename_length_cutoff = 100
        self.organization_classification = {
            Department: ["Referat"],
            Committee: ["Stadtratsgremium", "BA-Gremium", "Gremien"],
            ParliamentaryGroup: ["Fraktion", "Fraktionen"],
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
    def default_fields(libobject: OParl.Object):
        if libobject.get_deleted():
            return {
                "oparl_id": libobject.get_id(),
                "deleted": libobject.get_deleted(),
            }

        defaults = {
            "oparl_id": libobject.get_id(),
            "name": libobject.get_name(),
            "short_name": libobject.get_short_name() or libobject.get_name(),
            "deleted": libobject.get_deleted(),
        }

        # Add an ellipsis to not-so-short short names
        if len(defaults["short_name"]) > 50:
            defaults["short_name"] = defaults["short_name"][:47] + "\u2026"

        # FIXME: We can't just cut off official texts
        if len(defaults["name"]) > 200:
            defaults["name"] = defaults["name"].split("\n")[0]
        if len(defaults["name"]) > 200:
            defaults["name"] = defaults["name"][:200]

        return defaults

    @staticmethod
    def default_fields_new(libobject: OParl.Object, item: DefaultFields, name_fixup=None):
        item.oparl_id = libobject.get_id()
        item.name = libobject.get_name() or name_fixup
        item.short_name = libobject.get_short_name() or item.name
        item.deleted = libobject.get_deleted()

        # Add an ellipsis to not-so-short short names
        if len(item.short_name) > 50:
            item.short_name = item.short_name[:47] + "\u2026"

        # FIXME: We can't just cut off official texts
        if len(item.name) > 200:
            item.name = item.name.split("\n")[0]
        if len(item.name) > 200:
            item.name = item.name[:200]

        return item

    @classmethod
    def add_default_fields(cls, djangoobject: DefaultFields, libobject: OParl.Object):
        defaults = cls.default_fields(libobject)
        djangoobject.oparl_id = defaults["oparl_id"]
        if not defaults["deleted"]:
            djangoobject.name = defaults["name"]
            djangoobject.short_name = defaults["short_name"]
        djangoobject.deleted = defaults["deleted"]

    @staticmethod
    def get_organization_by_oparl_id(oparl_id):
        return Department.objects.filter(oparl_id=oparl_id).first() or \
               Committee.objects.filter(oparl_id=oparl_id).first() or \
               ParliamentaryGroup.objects.filter(oparl_id=oparl_id).first()

    # It seems that pycharm doesn't understand generics as in https://github.com/python/typing/issues/107
    # TODO: Check the pycharm bug tracker for that
    def check_existing(self, libobject: OParl.Object, constructor: Type[DefaultFields], add_defaults=True,
                       name_fixup=None):
        """ Checks common criterias for oparl objects. """
        if not libobject:
            return None

        dbobject = constructor.objects_with_deleted.filter(oparl_id=libobject.get_id()).first()  # type: DefaultFields
        if not dbobject:
            self.logger.debug("New")
            dbobject = constructor()
            if add_defaults:
                self.default_fields_new(libobject, dbobject, name_fixup)
            return dbobject

        if libobject.get_deleted():
            dbobject.deleted = True
            dbobject.save()
            self.logger.debug("Deleted")
            return None

        if not libobject.get_modified():
            error_message = "Modified missing on {}".format(libobject.get_id())
            self.errorlist.append(error_message)
        if libobject.get_modified() and dbobject.modified > self.glib_datetime_to_python(libobject.get_modified()):
            self.logger.debug("Not Modified")
            return None

        print("Modified")
        if add_defaults:
            self.default_fields_new(libobject, dbobject, name_fixup)
        return dbobject

    def extract_text_from_file(self, file: File):
        path = os.path.join(self.storagefolder, file.storage_filename)
        if file.mime_type == "application/pdf":
            print("Extracting text from PDF: " + path)
            try:
                text = extract_text_from_pdf(path, self.cachefolder)
                file.parsed_text = text
            except PDFTextExtractionNotAllowed:
                message = "The pdf {} is encrypted".format(path)
                self.errorlist.append(message)
        elif file.mime_type == "text/text":
            with open(path) as f:
                file.parsed_text = f.read()
