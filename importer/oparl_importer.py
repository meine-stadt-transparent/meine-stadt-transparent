import datetime

import gi
import requests

from mainapp.models import Body, LegislativeTerm

gi.require_version('OParl', '0.2')
from gi.repository import OParl


class OparlImporter:
    def __init__(self, entrypoint):
        self.entrypoint = entrypoint
        self.client = OParl.Client()
        self.client.connect("resolve_url", self.resolve)

    @staticmethod
    def resolve(_, url, status):
        try:
            print("Getting: " + url)
            req = requests.get(url)
            req.raise_for_status()
            return req.content.decode('utf-8')
        except Exception as e:
            print("error: ", e)
            return None

    def import_body(self, liboject: OParl.Body):
        print("Processing {}".format(liboject.get_name()))
        body = Body()
        body.name = liboject.get_name()
        body.short_name = liboject.get_short_name()
        body.deleted = liboject.get_deleted()
        body.oparl_id = liboject.get_id()
        # TODO: body.center

        terms = [self.import_term(term) for term in liboject.get_legislative_term()]
        body.legislative_terms = terms
        #body.save()
        return body

    def import_term(self, liboject: OParl.LegislativeTerm):
        print("Processing Term {}".format(liboject.get_short_name()))
        if not liboject.get_start_date() or not liboject.get_end_date():
            print("Term has no start or end date - skipping")
            return None
        term = LegislativeTerm()
        term.name = liboject.get_short_name()
        term.short_name = liboject.get_name()

        # FIXME

        term.start = datetime.datetime(liboject.get_start_date().format(""))
        term.end = datetime.datetime(liboject.get_end_date().format(""))
        #term.save()
        return term

    def import_paper(self, liboject: OParl.Paper):
        print("Stub Paper {}".format(liboject.get_id()))

    def run(self):
        system = self.client.open(self.entrypoint)
        bodies = system.get_body()

        for body in bodies:
            self.import_body(body)

            for paper in body.get_paper():
                self.import_paper(paper)
