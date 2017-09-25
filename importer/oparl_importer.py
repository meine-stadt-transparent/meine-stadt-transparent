import hashlib
import logging
import os
from collections import defaultdict
from datetime import date

import gi
import requests
from django.utils import dateparse

from mainapp.models import Body, LegislativeTerm, Paper, Department, Committee, ParliamentaryGroup, DefaultFields, \
    Meeting, Location, File, Person, AgendaItem

gi.require_version('OParl', '0.2')
from gi.repository import OParl
from gi.repository import GLib


class OParlImporter:
    def __init__(self, entrypoint, cachefolder, use_cache=True):
        self.cachefolder = cachefolder
        self.entrypoint = entrypoint
        self.client = OParl.Client()
        self.client.connect("resolve_url", self.resolve)
        self.use_cache = use_cache
        self.logger = logging.getLogger(__name__)
        self.download_files = True
        self.official_geojson = False

        # mappings that could not be resolved because the target object
        # hasn't been imported yet
        self.meeting_person_queue = defaultdict(list)
        self.agenda_item_paper_queue = {}

        os.makedirs(self.cachefolder, exist_ok=True)

    def resolve(self, client, url: str):
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
    def glib_date_to_python(glibdate: GLib.Date):
        if not glibdate:
            return None
        return date(glibdate.get_year(), glibdate.get_month(), glibdate.get_day())

    def add_default_fields(self, djangoobject: DefaultFields, libobject: OParl.Object):
        djangoobject.oparl_id = libobject.get_id()
        djangoobject.name = libobject.get_name()
        djangoobject.short_name = libobject.get_short_name() or libobject.get_name()
        djangoobject.deleted = libobject.get_deleted()

    def body(self, libobject: OParl.Body):
        print("Processing {}".format(libobject.get_name()))
        body, created = Body.objects.get_or_create(oparl_id=libobject.get_id())

        terms = []
        for term in libobject.get_legislative_term():
            saved_term = self.term(term)
            if saved_term:
                terms.append(saved_term)

        self.add_default_fields(body, libobject)
        body.oparl_id = libobject.get_id()
        body.legislative_terms = terms

        body.save()

        # TODO: geolocations

        return body

    def term(self, libobject: OParl.LegislativeTerm):
        print("Processing Term {}".format(libobject.get_name()))
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
        print("Processing Paper {}".format(libobject.get_id()))

        paper, created = Paper.objects.get_or_create(oparl_id=libobject.get_id())

        self.add_default_fields(paper, libobject)

        paper.save()

    def organization(self, libobject: OParl.Organization):
        print("Processing Organization {}".format(libobject.get_id()))

        classification = libobject.get_classification()
        if classification == "Referat":
            defaults = {"body": Body.objects.get(oparl_id=libobject.get_body().get_id())}
            organization, created = Department.objects.get_or_create(oparl_id=libobject.get_id(), defaults=defaults)
            self.add_default_fields(organization, libobject)
            assert not libobject.get_start_date() and not libobject.get_end_date()
        elif classification == "Stadtratsgremium":
            defaults = {"body": Body.objects.get(oparl_id=libobject.get_body().get_id())}
            organization, created = Committee.objects.get_or_create(oparl_id=libobject.get_id(), defaults=defaults)
            self.add_default_fields(organization, libobject)
            organization.start = self.glib_date_to_python(libobject.get_start_date())
            organization.end = self.glib_date_to_python(libobject.get_end_date())
        elif classification == "Fraktion":
            defaults = {"body": Body.objects.get(oparl_id=libobject.get_body().get_id())}
            organization, created = ParliamentaryGroup.objects.get_or_create(oparl_id=libobject.get_id(), defaults=defaults)
            self.add_default_fields(organization, libobject)
            organization.start = self.glib_date_to_python(libobject.get_start_date())
            organization.end = self.glib_date_to_python(libobject.get_end_date())
        else:
            self.logger.error("Unknown classification: {}".format(classification))
            return

        organization.save()

        return organization

    def meeting(self, libobject: OParl.Meeting):
        print("Processing Meeting {}".format(libobject.get_id()))
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
            djangoperson = Person.objects.get(oparl_id=oparlperson.get_id())
            if djangoperson:
                persons.append(djangoperson)
            else:
                self.meeting_person_queue[libobject.get_id()].append(oparlperson.get_id())
        meeting.persons = persons

        agenda_items = []
        for index, oparlitem in enumerate(libobject.get_agenda_item()):
            djangoitem = self.agendaitem(oparlitem, index)
            if djangoitem:
                agenda_items.append(djangoitem)
        meeting.agenda_items = agenda_items

        meeting.save()

        return meeting

    def location(self, libobject: OParl.Location):
        if not libobject:
            return None

        location = Location.objects.filter(oparl_id=libobject.get_id()).first() or Location()
        location.oparl_id = libobject.get_id()
        location.name = "TODO: FIXME"
        location.short_name = "FIXME"
        location.description = libobject.get_description()
        location.is_official = self.official_geojson

        # FIXME: Actual geojson

        location.save()

        return location

    def agendaitem(self, libobject: OParl.AgendaItem, index):
        if not libobject:
            return None

        item, created = AgendaItem.objects.get_or_create(oparl_id=libobject.get_id())
        item.position = index
        item.key = libobject.get_number()
        item.public = libobject.get_public()

        paper = Paper.objects.get(oparl_id=libobject.get_consultation().get_paper())
        if paper:
            item.paper = paper
        else:
            self.agenda_item_paper_queue[libobject.get_id()] = libobject.get_consultation().get_paper()
        return item

    def file(self, libobject: OParl.File):
        if not libobject:
            return None
        file = File.objects.filter(oparl_id=libobject.get_id()).first() or File()

        file.name = libobject.get_name()
        file.displayed_filename = libobject.get_file_name()
        file.storage_filename = "NOT IMPLEMENTED"
        file.parsed_text = libobject.get_text()
        file.mime_type = libobject.get_mime_type()
        file.legal_date = libobject.get_date()
        file.filesize = 0  # FIXME

        file.save()

        return file
        # TODO: Download the file

    def person(self, libobject: OParl.Person):
        person, created = Person.objects.get_or_create(oparl_id=libobject.get_id())

        person.name = libobject.get_name()
        person.given_name = libobject.get_given_name()
        person.family_name = libobject.get_family_name()
        person.location = self.location(libobject.get_location())

    def body_lists(self, body: OParl.Body):
        for paper in body.get_paper():
            self.paper(paper)

        for person in body.get_person():
            self.person(person)

        for organization in body.get_organization():
            self.organization(organization)

        for meeting in body.get_meeting():
            self.meeting(meeting)

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
        for body in bodies:
            self.body(body)

        print("Finished creating bodies")

        for body in bodies:
            self.body_lists(body)

        for meeting_id, person_ids in self.meeting_person_queue.items():
            print("Adding missing meeting <-> persons associations")
            meeting = Meeting.objects.get(oparl_id=meeting_id)
            meeting.persons = [Person.objects.get(oparl_id=person_id) for person_id in person_ids]
            meeting.save()

        for item_id, paper_id in self.agenda_item_paper_queue:
            print("Adding missing agenda item <-> persons associations")
            item = AgendaItem.objects.get(oparl_id=item_id)
            item.paper = Paper.objects.get(oparl_id=paper_id)
            item.save()
