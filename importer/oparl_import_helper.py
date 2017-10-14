import hashlib
import json
import os
from datetime import date

import gi
from django.utils import dateparse

from mainapp.models import DefaultFields
from mainapp.models import Department, Committee, ParliamentaryGroup

gi.require_version('OParl', '0.2')
gi.require_version('Json', '1.0')
from gi.repository import Json, GLib, OParl


class OParlImportHelper:
    """ A collection of helper function for the oparl importer.

    These are methods and not functions so they can be easily overwritten.
    """
    def __init__(self, options):
        self.storagefolder = options["storagefolder"]
        self.entrypoint = options["entrypoint"]
        self.use_cache = options["use_cache"]
        self.download_files = options["download_files"]
        self.with_persons = options["with-persons"]
        self.with_papers = options["with-papers"]
        self.with_organizations = options["with-organizations"]
        self.with_meetings = options["with-meetings"]
        self.threadcount = options["threadcount"]
        self.batchsize = options["batchsize"]
        entrypoint_hash = hashlib.sha1(self.entrypoint.encode("utf-8")).hexdigest()
        self.cachefolder = os.path.join(options["cachefolder"], entrypoint_hash)
        self.download_files = options["download-files"]
        self.official_geojson = False
        self.organization_classification = {
            Department: ["Referat"],
            Committee: ["Stadtratsgremium", "BA-Gremium", "Gremien"],
            ParliamentaryGroup: ["Fraktion", "Fraktionen"],
        }

    @staticmethod
    def extract_geometry(glib_json: Json.Object):
        """ Extracts the geometry part of the geojson as python object. A bit ugly. """
        if not glib_json:
            return None
        node = glib_json.get_member('geometry')
        return json.loads(Json.to_string(node, True))

    @staticmethod
    def glib_datetime_to_python(glibdatetime: GLib.DateTime):
        if not glibdatetime:
            return None
        return dateparse.parse_datetime(glibdatetime.format("%FT%T%z"))

    @staticmethod
    def glib_datetime_to_python_date(glibdatetime: GLib.DateTime):
        # TODO: Remove once https://github.com/OParl/liboparl/issues/18 is fixed
        if not glibdatetime:
            return None
        return date(glibdatetime.get_year(), glibdatetime.get_month(), glibdatetime.get_day_of_month())

    @staticmethod
    def glib_date_to_python(glibdate: GLib.Date):
        if not glibdate:
            return None
        return date(glibdate.get_year(), glibdate.get_month(), glibdate.get_day())

    @classmethod
    def glib_datetime_or_date_to_python(cls, glibdate):
        if isinstance(glibdate, GLib.Date):
            return cls.glib_date_to_python(glibdate)
        if isinstance(glibdate, GLib.DateTime):
            return cls.glib_datetime_to_python_date(glibdate)
        return None

    @staticmethod
    def add_default_fields(djangoobject: DefaultFields, libobject: OParl.Object):
        djangoobject.oparl_id = libobject.get_id()
        djangoobject.name = libobject.get_name()

        # FIXME: We can't just cut off official texts
        if len(djangoobject.name) > 200:
            djangoobject.name = djangoobject.name.split("\n")[0]
        if len(djangoobject.name) > 200:
            djangoobject.name = djangoobject.name[:200]

        djangoobject.short_name = libobject.get_short_name() or libobject.get_name()
        djangoobject.short_name = djangoobject.short_name[:50]
        djangoobject.deleted = libobject.get_deleted()

    @staticmethod
    def add_default_fields_dict(djangoobject: dict, libobject: OParl.Object):
        """ TODO: That's code duplication """
        djangoobject["oparl_id"] = libobject.get_id()
        djangoobject["name"] = libobject.get_name()

        # FIXME: We can't just cut off official texts
        if len(djangoobject["name"]) > 200:
            djangoobject["name"] = djangoobject["name"].split("\n")[0]
        if len(djangoobject["name"]) > 200:
            djangoobject["name"] = djangoobject["name"][:200]

        djangoobject["short_name"] = libobject.get_short_name() or libobject.get_name()
        djangoobject["short_name"] = djangoobject["short_name"][:50]
        djangoobject["deleted"] = libobject.get_deleted()