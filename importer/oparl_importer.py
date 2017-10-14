import concurrent
import hashlib
import json
import logging
import os
import sys
import traceback
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor as Pool
from datetime import date
from typing import Callable, TypeVar

import gi
import requests
from django.db import transaction
from django.utils import dateparse
from django.utils.translation import ugettext as _

from mainapp.models import Body, LegislativeTerm, Paper, Department, Committee, ParliamentaryGroup, DefaultFields, \
    Meeting, Location, File, Person, AgendaItem
from mainapp.models.committee_membership import CommitteeMembership
from mainapp.models.department_membership import DepartmentMembership
from mainapp.models.parliamentary_group_membership import ParliamentaryGroupMembership

gi.require_version('OParl', '0.2')
from gi.repository import OParl
from gi.repository import GLib
from gi.repository import Json


class OParlImporter:
    def __init__(self, options):
        # Config
        self.storagefolder = options["storagefolder"]
        self.entrypoint = options["entrypoint"]
        self.use_cache = options["use_cache"]
        self.download_files = options["download_files"]
        self.with_persons = options["with-persons"]
        self.with_papers = options["with-papers"]
        self.with_organizations = options["with-organizations"]
        self.with_meetings = options["with-meetings"]
        self.threadcount = options["threadcount"]
        entrypoint_hash = hashlib.sha1(self.entrypoint.encode("utf-8")).hexdigest()
        self.cachefolder = os.path.join(options["cachefolder"], entrypoint_hash)
        self.download_files = options["download-files"]
        self.official_geojson = False
        self.organization_classification = {
            Department: ["Referat"],
            Committee: ["Stadtratsgremium", "BA-Gremium", "Gremien"],
            ParliamentaryGroup: ["Fraktion", "Fraktionen"],
        }

        # Setup
        self.logger = logging.getLogger(__name__)
        self.client = OParl.Client()

        self.client.connect("resolve_url", self.resolve)
        os.makedirs(self.storagefolder, exist_ok=True)
        os.makedirs(self.cachefolder, exist_ok=True)

        # mappings that could not be resolved because the target object
        # hasn't been imported yet
        self.meeting_person_queue = defaultdict(list)
        self.agenda_item_paper_queue = {}
        self.membership_queue = []

    @staticmethod
    def extract_geometry(glib_json: Json.Object):
        """ Extracts the geometry part of the geojson as python object. A bit ugly. """
        if not glib_json:
            return None
        node = glib_json.get_member('geometry')
        return json.loads(Json.to_string(node, True))

    def resolve(self, _, url: str):
        cachepath = os.path.join(self.cachefolder, hashlib.sha1(url.encode('utf-8')).hexdigest())
        if self.use_cache and os.path.isfile(cachepath):
            print("Cached: " + url)
            with open(cachepath) as file:
                data = file.read()
                return OParl.ResolveUrlResult(resolved_data=data, success=True, status_code=304)

        try:
            print("Loading: " + url)
            req = requests.get(url)
        except Exception as e:
            self.logger.error("Error loading url: ", e)
            return OParl.ResolveUrlResult(resolved_data=None, success=False, status_code=-1)

        content = req.content.decode('utf-8')

        try:
            req.raise_for_status()
        except Exception as e:
            self.logger.error("HTTP status code error: ", e)
            return OParl.ResolveUrlResult(resolved_data=content, success=False, status_code=req.status_code)

        with open(cachepath, 'w') as file:
            file.write(content)

        return OParl.ResolveUrlResult(resolved_data=content, success=True, status_code=req.status_code)

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

    @staticmethod
    def glib_datetime_or_date_to_python(glibdate):
        if isinstance(glibdate, GLib.Date):
            return OParlImporter.glib_date_to_python(glibdate)
        if isinstance(glibdate, GLib.DateTime):
            return OParlImporter.glib_datetime_to_python_date(glibdate)
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

    def body(self, libobject: OParl.Body):
        self.logger.info("Processing {}".format(libobject.get_name()))
        body, created = Body.objects.get_or_create(oparl_id=libobject.get_id())

        terms = []
        for term in libobject.get_legislative_term():
            saved_term = self.term(term)
            if saved_term:
                terms.append(saved_term)

        self.add_default_fields(body, libobject)
        body.oparl_id = libobject.get_id()
        body.legislative_terms = terms

        location = self.location(libobject.get_location())
        if location and location.geometry:
            if location.geometry["type"] == "Point":
                body.center = location
            elif location.geometry["type"] == "Polygon":
                body.outline = location
            else:
                self.logger.warning("Location object is of type {}, which is neither 'Point' nor 'Polygon'. Skipping "
                                    "this location.".format(location.geometry["type"]))

        body.save()

        return body

    def term(self, libobject: OParl.LegislativeTerm):
        if not libobject.get_start_date() or not libobject.get_end_date():
            self.logger.error("Term has no start or end date - skipping")
            return None

        term = LegislativeTerm.objects.filter(oparl_id=libobject.get_id()).first() or LegislativeTerm()

        term.name = libobject.get_name()
        term.short_name = libobject.get_short_name() or libobject.get_name()
        term.start = dateparse.parse_datetime(libobject.get_start_date().format("%FT%T%z"))
        term.end = dateparse.parse_datetime(libobject.get_end_date().format("%FT%T%z"))

        term.save()

        return term

    def paper(self, libobject: OParl.Paper):
        self.logger.info("Processing Paper {}".format(libobject.get_id()))

        defaults = {
            # TODO: Here's surely some fields missing
            "legal_date": self.glib_datetime_to_python_date(libobject.get_date())
        }
        self.add_default_fields_dict(defaults, libobject)

        paper, _ = Paper.objects.update_or_create(oparl_id=libobject.get_id(), defaults=defaults)
        paper.files = [self.file(file) for file in libobject.get_auxiliary_file()]
        paper.main_file = self.file(libobject.get_main_file())

        return paper

    def organization(self, libobject: OParl.Organization):
        self.logger.info("Processing Organization {}".format(libobject.get_id()))

        classification = libobject.get_classification()
        if classification in self.organization_classification[Department]:
            defaults = {"body": Body.by_oparl_id(libobject.get_body().get_id())}
            organization, created = Department.objects.get_or_create(oparl_id=libobject.get_id(), defaults=defaults)
            self.add_default_fields(organization, libobject)
            assert not libobject.get_start_date() and not libobject.get_end_date()
        elif classification in self.organization_classification[Committee]:
            defaults = {"body": Body.by_oparl_id(libobject.get_body().get_id())}
            organization, created = Committee.objects.get_or_create(oparl_id=libobject.get_id(), defaults=defaults)
            self.add_default_fields(organization, libobject)
            organization.start = self.glib_datetime_or_date_to_python(libobject.get_start_date())
            organization.end = self.glib_datetime_or_date_to_python(libobject.get_end_date())
        elif classification in self.organization_classification[ParliamentaryGroup]:
            defaults = {"body": Body.by_oparl_id(libobject.get_body().get_id())}
            organization, created = ParliamentaryGroup.objects.get_or_create(oparl_id=libobject.get_id(),
                                                                             defaults=defaults)
            self.add_default_fields(organization, libobject)
            organization.start = self.glib_datetime_or_date_to_python(libobject.get_start_date())
            organization.end = self.glib_datetime_or_date_to_python(libobject.get_end_date())
        else:
            self.logger.error("Unknown Classification: {} ({})".format(classification, libobject.get_id()))
            return

        for membership in libobject.get_membership():
            self.membership(classification, organization, membership)

        organization.save()

        return organization

    def meeting(self, libobject: OParl.Meeting):
        self.logger.info("Processing Meeting {}".format(libobject.get_id()))
        meeting = Meeting.objects.filter(oparl_id=libobject.get_id()).first() or Meeting()
        self.add_default_fields(meeting, libobject)
        meeting.start = self.glib_datetime_to_python(libobject.get_start())
        meeting.end = self.glib_datetime_to_python(libobject.get_end())
        meeting.location = self.location(libobject.get_location())
        meeting.invitation = self.file(libobject.get_invitation())
        meeting.verbatim_protocol = self.file(libobject.get_verbatim_protocol())
        meeting.results_protocol = self.file(libobject.get_results_protocol())
        meeting.cancelled = libobject.get_cancelled() or False

        meeting.save()

        auxiliary_files = []
        for oparlfile in libobject.get_auxiliary_file():
            djangofile = self.file(oparlfile)
            if djangofile:
                auxiliary_files.append(djangofile)
        meeting.auxiliary_files = auxiliary_files

        persons = []
        for oparlperson in libobject.get_participant():
            djangoperson = Person.by_oparl_id(oparlperson.get_id())
            if djangoperson:
                persons.append(djangoperson)
            else:
                self.meeting_person_queue[libobject.get_id()].append(oparlperson.get_id())
        meeting.persons = persons

        for index, oparlitem in enumerate(libobject.get_agenda_item()):
            self.agendaitem(oparlitem, index, meeting)

        meeting.save()

        return meeting

    def location(self, libobject: OParl.Location):
        if not libobject:
            return None

        self.logger.info("Processing Location {}".format(libobject.get_id()))

        location = Location.objects.filter(oparl_id=libobject.get_id()).first() or Location()
        location.oparl_id = libobject.get_id()
        location.name = "TODO: FIXME"
        location.short_name = "FIXME"
        location.description = libobject.get_description()
        location.is_official = self.official_geojson
        location.geometry = self.extract_geometry(libobject.get_geojson())
        location.save()

        return location

    def agendaitem(self, libobject: OParl.AgendaItem, index, meeting):
        if not libobject:
            return None

        paper = None
        if libobject.get_consultation() and libobject.get_consultation().get_paper():
            paper = Paper.objects.filter(oparl_id=libobject.get_consultation().get_paper()).first()
            if not paper:
                self.agenda_item_paper_queue[libobject.get_id()] = libobject.get_consultation().get_paper()

        item_key = libobject.get_number()
        if not item_key:
            item_key = "-"
        
        values = {
            "title": libobject.get_name(),
            "position": index,
            "meeting": meeting,
            "oparl_id": libobject.get_id(),
            "key": item_key,
            "public": libobject.get_public(),
            "paper": paper,
        }

        item, created = AgendaItem.objects.update_or_create(oparl_id=libobject.get_id(), defaults=values)

        return item

    def download_file(self, file: File, libobject: OParl.File):
        if file.modified and self.glib_datetime_to_python(libobject.get_modified()) < file.modified:
            print("Cached Donwload: {}".format(libobject.get_download_url()))
            return

        print("Downloading {}".format(libobject.get_download_url()))

        urlhash = hashlib.sha1(libobject.get_id().encode("utf-8")).hexdigest()
        path = os.path.join(self.storagefolder, urlhash)

        r = requests.get(libobject.get_download_url(), allow_redirects=True)
        r.raise_for_status()
        open(path, 'wb').write(r.content)

        file.filesize = os.stat(path).st_size
        file.storage_filename = urlhash

    def file(self, libobject: OParl.File):
        if not libobject:
            return None

        self.logger.info("Processing File {}".format(libobject.get_id()))

        displayed_filename = libobject.get_file_name()
        if not displayed_filename:
            displayed_filename = _("Unknown")
        
        file = File.objects.filter(oparl_id=libobject.get_id()).first() or File()

        file.oparl_id = libobject.get_id()
        file.name = libobject.get_name()[:200]  # FIXME
        file.displayed_filename = displayed_filename
        file.parsed_text = libobject.get_text()
        file.mime_type = libobject.get_mime_type() or "application/octet-stream"
        file.legal_date = self.glib_datetime_to_python_date(libobject.get_date())

        if self.download_files:
            self.download_file(file, libobject)
        else:
            file.storage_filename = "FILE NOT DOWNLOADED"
            file.filesize = -1

        file.save()

        return file

    def person(self, libobject: OParl.Person):
        self.logger.info("Processing Person {}".format(libobject.get_id()))

        person, created = Person.objects.get_or_create(oparl_id=libobject.get_id())

        person.name = libobject.get_name()
        person.given_name = libobject.get_given_name()
        person.family_name = libobject.get_family_name()
        person.location = self.location(libobject.get_location())
        person.save()

    def body_paper(self, body: OParl.Body):
        if not self.with_papers:
            return

        for paper in body.get_paper():
            self.paper(paper)

    def body_person(self, body: OParl.Body):
        for person in body.get_person():
            self.person(person)

    def body_organization(self, body: OParl.Body):
        for organization in body.get_organization():
            self.organization(organization)

    def body_meeting(self, body: OParl.Body):
        if not self.with_meetings:
            return

        for meeting in body.get_meeting():
            self.meeting(meeting)

    def add_missing_associations(self):
        for meeting_id, person_ids in self.meeting_person_queue.items():
            print("Adding missing meeting <-> persons associations")
            meeting = Meeting.by_oparl_id(meeting_id)
            meeting.persons = [Person.by_oparl_id(person_id) for person_id in person_ids]
            meeting.save()

        for item_id, paper_id in self.agenda_item_paper_queue:
            print("Adding missing agenda item <-> persons associations")
            item = AgendaItem.objects.get(oparl_id=item_id)
            item.paper = Paper.by_oparl_id(paper_id)
            item.save()

        for classification, organization, libobject in self.membership_queue:
            print("Adding missing memberships")
            self.membership(classification, organization, libobject)

    def membership(self, classification, organization, libobject: OParl.Membership):
        person = Person.objects.filter(oparl_id=libobject.get_person().get_id()).first()
        if not person:
            self.membership_queue.append((classification, organization, libobject))
            return None

        role = libobject.get_role()
        if not role:
            role = _("Unknown")

        defaults = {
            "person": person,
            "start": self.glib_datetime_to_python_date(libobject.get_start_date()),
            "end": self.glib_datetime_to_python_date(libobject.get_end_date()),
            "role": role,
        }

        if classification in self.organization_classification[Department]:
            defaults["department"] = organization
            membership = DepartmentMembership.objects.get_or_create(oparl_id=libobject.get_id(), defaults=defaults)
        elif classification in self.organization_classification[Committee]:
            defaults["committee"] = organization
            membership = CommitteeMembership.objects.get_or_create(oparl_id=libobject.get_id(), defaults=defaults)
        elif classification in self.organization_classification[ParliamentaryGroup]:
            defaults["parliamentary_group"] = organization
            membership = ParliamentaryGroupMembership.objects.get_or_create(oparl_id=libobject.get_id(), defaults=defaults)
        else:
            self.logger.error("Unknown Classification: {} ({})".format(classification, libobject.get_id()))
            return

        return membership

    T = TypeVar('T')

    @staticmethod
    def reraise(fn: Callable[[T], None], arg: T):
        """ Raise exceptions in threads immediately """
        try:
            fn(arg)
        except Exception as e:
            print("An error occured:", e)
            traceback.print_exc()

    def run_singlethread(self):
        try:
            system = self.client.open(self.entrypoint)
        except GLib.Error as e:
            self.logger.fatal("Failed to load entrypoint: {}".format(e))
            self.logger.fatal("Aborting.")
            return
        bodies = system.get_body()

        print("Creating bodies")
        for body in bodies:
            self.body(body)
        print("Finished creating bodies")

        print("Creating objects")
        for body in bodies:
            if self.with_papers:
                self.body_paper(body)
            if self.with_persons:
                self.body_person(body)
            if self.with_organizations:
                self.body_organization(body)
            if self.with_meetings:
                self.body_meeting(body)

        print("Finished creating objects")
        self.add_missing_associations()

    def run(self):
        try:
            system = self.client.open(self.entrypoint)
        except GLib.Error as e:
            self.logger.fatal("Failed to load entrypoint: {}".format(e))
            self.logger.fatal("Aborting.")
            return
        bodies = system.get_body()

        print("Creating bodies")
        # Ensure all bodies exist when calling the other methods

        with Pool(self.threadcount) as executor:
            results = executor.map(self.body, bodies)

        # Raise those exceptions
        list(results)
        print("Finished creating bodies")

        with Pool(self.threadcount) as executor:
            print("Submitting concurrent tasks")
            futures = {}
            for body in bodies:
                if self.with_papers:
                    futures[executor.submit(self.reraise, self.body_paper, body)] = "{}: Paper".format(body.get_short_name())
                if self.with_persons:
                    futures[executor.submit(self.reraise, self.body_person, body)] = "{}: Person".format(body.get_short_name())
                if self.with_organizations:
                    futures[executor.submit(self.reraise, self.body_organization, body)] = "{}: Organization".format(body.get_short_name())
                if self.with_meetings:
                    futures[executor.submit(self.reraise, self.body_meeting, body)] = "{}: Meeting".format(body.get_short_name())
            print("Finished submitting concurrent tasks")
            for future in concurrent.futures.as_completed(futures):
                print("Finished", futures[future])
                future.result()

        print("Finished creating objects")
        self.add_missing_associations()

    @classmethod
    def run_static(cls, config):
        """ This method is requried as instances of this class can't be moved to other processes """
        try:
            runner = cls(config)
            runner.run()
        except Exception:
            print("There was an error in the Process for {}".format(config["entrypoint"]), file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            return False
        return True

