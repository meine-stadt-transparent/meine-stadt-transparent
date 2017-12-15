import logging

import requests
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from importer import CityToAGS
from importer.citytools import import_streets, import_outline
from importer.functions import get_importer
from importer.oparl_helper import default_options
from mainapp.models import Body
from meine_stadt_transparent import settings

logger = logging.getLogger(__name__)


class OParlAuto:

    @staticmethod
    def endpoints():
        next_page = settings.OPARL_ENDPOINTS_LIST
        while next_page:
            response = requests.get(next_page).json()
            next_page = response["meta"].get("next", None)
            for i in response["data"]:
                yield i

    @classmethod
    def magic_import(cls, userinput):
        """ It's magic in the disney sense """
        try:
            URLValidator()(userinput)
            is_url = True
        except ValidationError:
            is_url = False

        if is_url:
            logging.info("Found url, importing url")
            raise NotImplementedError()

        endpoint_id, endpoint_system = cls.get_endpoint(userinput)

        importer, liboparl_body = cls.get_importer_with_body(endpoint_id, endpoint_system)

        ags = cls.get_ags(liboparl_body, userinput)

        cls.do_import(ags, importer, liboparl_body)

    @classmethod
    def get_importer_with_body(cls, endpoint_id, endpoint_system):
        """ Get the oparl importer and the body as liboparl object """
        liboparl_body = None
        options = default_options.copy()
        options["entrypoint"] = endpoint_system
        importer = get_importer()(options)
        bodies = importer.get_bodies()
        for body in bodies:
            if body.get_id() == endpoint_id:
                liboparl_body = body
                break
        if not liboparl_body:
            raise Exception("Failed to find body {} in {} even though the {} says it is there"
                            .format(endpoint_id, endpoint_system, settings.OPARL_ENDPOINTS_LIST))
        return importer, liboparl_body

    @classmethod
    def do_import(cls, ags, importer, liboparl_body):
        logger.info("Importing {}".format(liboparl_body.get_id()))
        main_body = importer.body(liboparl_body)
        logger.info("We're done with the OParl import. We just need some metadata now")
        import_streets(main_body, ags)
        import_outline(main_body, ags)
        logger.info("Done! Please add the following line to your dotenv file: \nSITE_DEFAULT_BODY={}"
                    .format(main_body.id))

    @classmethod
    def get_ags(cls, liboparl_body, userinput):
        ags = liboparl_body.get_ags()
        if not ags:
            ags = CityToAGS.query_wikidata(userinput)
        if not ags:
            raise Exception("Could not find the Gemeindeschlüssel for '{}'".format(userinput))
        logging.info("Using {} as Gemeindeschlüssel for '{}'".format(ags, userinput))
        return ags

    @classmethod
    def get_endpoint(cls, userinput):
        matching = []
        for system in cls.endpoints():
            for body in system["bodies"]:
                if userinput.casefold() in body["name"].casefold():
                    matching.append((system["system"], body))
        if len(matching) == 0:
            raise Exception("Could not find anything for '{}'".format(userinput))
        if len(matching) > 1:
            exact_matches = [i for i in matching if i[1]["name"] == userinput]
            if len(exact_matches) == 1:
                matching = exact_matches
            else:
                raise Exception(("There are {} matches for your input and I can't decide which one to use. " +
                                 "Please provide a url yourself").format(len(matching)))
        endpoint = matching[0]
        return endpoint[1]["oparl_id"], endpoint[0]["id"]
