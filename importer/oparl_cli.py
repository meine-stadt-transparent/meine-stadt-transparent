import logging

import requests
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from importer import CityToAGS
from importer.citytools import import_streets, import_outline
from importer.functions import get_importer
from importer.oparl_helper import default_options
from meine_stadt_transparent import settings

logger = logging.getLogger(__name__)


class OParlCli:
    """ Tries to import all required data (oparl system id, ags and city name for osm) from a user input
    that might be the name of a city, the url of a body or the url of a system.

    It uses the joint information the oparl dev portal and the oparl mirror.
    """

    @staticmethod
    def bodies():
        for next_page in settings.OPARL_ENDPOINTS_LIST:
            while next_page:
                print(next_page)
                response = requests.get(next_page).json()
                # links for mirror.oparl.org, meta is for dev.oparl.org
                if "links" in response:
                    next_page = response["links"].get("next")
                    for body in response["data"]:
                        yield (None, body["oparl-mirror:originalId"], body)
                elif "meta" in response:
                    next_page = response["meta"].get("next")
                    for system in response["data"]:
                        for body in system["bodies"]:
                            yield (system["system"], body["oparlURL"], body)
                else:
                    logger.error("Expected links or pagination")
                    next_page = None

    @classmethod
    def from_userinput(cls, userinput):
        """ It's magic in the disney sense """
        try:
            URLValidator()(userinput)
            is_url = True
        except ValidationError:
            is_url = False

        if not is_url:
            endpoint_id, endpoint_system = cls.get_endpoint_from_cityname(userinput)
        else:
            endpoint_id, endpoint_system = cls.get_endpoint_from_body_url(userinput)

        importer, liboparl_body = cls.get_importer_with_body(endpoint_id, endpoint_system)

        ags = cls.get_ags(liboparl_body, userinput)

        cls.run_importer(ags, importer, liboparl_body)

    @classmethod
    def get_endpoint_from_body_url(cls, userinput):
        # We can't use the resolver here as we don't know the system url yet, which the resolver needs for determining
        # the cache folder
        logging.info("Found url, importing url")
        response = requests.get(userinput)
        response.raise_for_status()
        if response.json().get("type") != "https://schema.oparl.org/1.0/Body":
            raise Exception("The url you provided didn't point to an oparl body")
        endpoint_system = response.json()["system"]
        endpoint_id = userinput
        return endpoint_id, endpoint_system

    @classmethod
    def get_importer_with_body(cls, endpoint_id, endpoint_system):
        """ Get the oparl importer and the body as liboparl object """
        liboparl_body = None
        options = default_options.copy()

        options["entrypoint"] = endpoint_system
        importer = get_importer(options)
        bodies = importer.get_bodies()
        for body in bodies:
            if body.get_id() == endpoint_id:
                liboparl_body = body
                break
        if not liboparl_body:
            raise Exception("Failed to find body {} in {}".format(endpoint_id, endpoint_system))
        return importer, liboparl_body

    @classmethod
    def run_importer(cls, ags, importer, liboparl_body):
        logger.info("Importing {}".format(liboparl_body.get_id()))
        main_body = importer.body(liboparl_body)

        logger.info("Finished importing body")
        importer.list_batched(liboparl_body.get_paper, importer.paper)
        importer.list_batched(liboparl_body.get_person, importer.person)
        importer.list_batched(liboparl_body.get_organization, importer.organization)
        importer.list_batched(liboparl_body.get_meeting, importer.meeting)

        logger.info("Finished importing objects")
        importer.add_missing_associations()

        logger.info("We're done with the OParl import. We just need some metadata now")
        import_streets(main_body, ags)
        import_outline(main_body, ags)

        dotenv = "SITE_DEFAULT_BODY={}".format(main_body.id) + "\n" \
                 + "OPARL_ENDPOINT={}".format(importer.entrypoint)

        logger.info("Done! Please add the following line to your dotenv file: \n" + dotenv)

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
    def get_endpoint_from_cityname(cls, userinput):
        matching = []
        for (system_id, body_id, body) in cls.bodies():
            if userinput.casefold() in body["name"].casefold():
                # The oparl mirror doesn't give us the system id we need
                if not system_id:
                    response = requests.get(body_id)
                    response.raise_for_status()
                    system_id = response.json()["system"]
                matching.append((body_id, system_id))
        if len(matching) == 0:
            raise Exception("Could not find anything for '{}'".format(userinput))
        if len(matching) > 1:
            exact_matches = [i for i in matching if i[0]["name"] == userinput]
            if len(exact_matches) == 1:
                matching = exact_matches
            else:
                raise Exception(("There are {} matches for your input and I can't decide which one to use. " +
                                 "Please provide a url yourself").format(len(matching)))
        return matching[0]
