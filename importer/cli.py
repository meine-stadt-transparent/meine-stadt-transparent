import logging
from typing import Tuple, List

import requests
from django import db
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from importer import JSON
from importer.importer import Importer
from importer.loader import get_loader_from_system
from mainapp.functions.city_to_ags import city_to_ags
from mainapp.functions.citytools import import_outline, import_streets
from mainapp.models import Body
from meine_stadt_transparent import settings

logger = logging.getLogger(__name__)


class Cli:
    """ Tries to import all required data (oparl system id, ags and city name for osm) from a user input
    that might be the name of a city, the url of a body or the url of a system.

    It uses the information from wikidata, open street map and the oparl mirror.
    """

    def __init__(self):
        self.bodies = []  # type: List[Tuple[str, str, str]]

        next_page = settings.OPARL_INDEX
        while next_page:
            response = requests.get(next_page)
            response.raise_for_status()
            data = response.json()
            next_page = data["links"].get("next")
            for body in data["data"]:
                if not "oparl-mirror:originalId" in body:
                    continue
                self.bodies.append(
                    (
                        body.get("name") or body["oparl-mirror:originalId"],
                        body["oparl-mirror:originalId"],
                        body["id"],
                    )
                )

    def from_userinput(self, userinput: str, mirror: bool) -> None:
        body_id, entrypoint = self.get_entrypoint_and_body(userinput, mirror)
        importer = Importer(get_loader_from_system(entrypoint))
        body_data, dotenv = self.import_body_and_metadata(body_id, importer, userinput)

        logger.info("Loading the bulk data from the oparl api")
        importer.fetch_lists_initial([body_data])

        # Also avoid "MySQL server has gone away" errors due to timeouts
        # https://stackoverflow.com/a/32720475/3549270
        db.close_old_connections()

        logger.info("Loading the data into the database")
        importer.import_objects()

        logger.info("Loading the files")
        importer.load_files(fallback_city=userinput)

        if dotenv:
            logger.info(
                "Done! Please add the following line to your dotenv file: \n\n"
                + dotenv
                + "\n"
            )

    def import_body_and_metadata(
        self, body_id: str, importer: Importer, userinput: str
    ) -> Tuple[JSON, str]:
        logger.info("Fetching the body {}".format(body_id))
        [body_data] = importer.load_bodies(body_id)
        logger.info("Importing the body")
        [body] = importer.import_bodies()
        importer.converter.default_body = body
        logger.info("Looking up the Amtliche Gemeindeschlüssel")
        ags = self.get_ags(body, userinput)
        logger.info(
            "Using {} as Amtliche Gemeindeschlüssel for '{}'".format(ags, userinput)
        )
        dotenv = ""
        if settings.GEOEXTRACT_DEFAULT_CITY != userinput:
            dotenv += "GEOEXTRACT_DEFAULT_CITY={}\n".format(userinput)
        if body.id != settings.SITE_DEFAULT_BODY:
            dotenv += "SITE_DEFAULT_BODY={}\n".format(body.id)
        if dotenv:
            logger.info(
                "Found the oparl endpoint. Please add the following line to your dotenv file "
                "(you'll be reminded again after the import finished): \n\n" + dotenv
            )
        logger.info("Importing the shape of the city")
        import_outline(body, ags)
        logger.info("Importing the streets")
        import_streets(body, ags)
        return body_data.data, dotenv

    def get_entrypoint_and_body(self, userinput: str, mirror: bool) -> Tuple[str, str]:
        try:
            URLValidator()(userinput)
            is_url = True
        except ValidationError:
            is_url = False
        if not is_url:
            entrypoint, body_id = self.get_endpoint_from_cityname(userinput, mirror)
        else:
            entrypoint, body_id = self.get_endpoint_from_body_url(userinput)

        logger.info(
            "Your body id is {} and your system id is {}".format(body_id, entrypoint)
        )

        return body_id, entrypoint

    def get_endpoint_from_body_url(self, userinput: str) -> Tuple[str, str]:
        # We can't use the resolver here as we don't know the system url yet, which the resolver needs for determining
        # the cache folder
        logging.info("Using {} as url".format(userinput))
        response = requests.get(userinput)
        response.raise_for_status()
        data = response.json()
        if data.get("type") != "https://schema.oparl.org/1.0/Body":
            raise RuntimeError("The url you provided didn't point to an oparl body")
        endpoint_system = data["system"]
        endpoint_id = userinput
        return endpoint_system, endpoint_id

    def get_ags(self, body: Body, userinput: str) -> str:
        ags = body.ags
        # The len(ags) check is necessary because there's Kall and Jülich
        # which failed to add the leading zero
        # https://sdnetrim.kdvz-frechen.de/rim4550/webservice/oparl/v1/body
        if not ags or len(ags) != 8:
            # Open question: Are there cases where this only works with the user input and not with the short name?
            ags_list = city_to_ags(body.short_name)
            if len(ags_list) == 0:
                raise RuntimeError(
                    "Could not find the Gemeindeschlüssel for '{}'".format(userinput)
                )
            if len(ags_list) > 1:
                raise RuntimeError(
                    "Found more than one Gemeindeschlüssel for '{}': {}".format(
                        userinput, ags_list
                    )
                )
            ags = ags_list[0][1]
            body.ags = ags
            body.save()

        return ags

    def get_endpoint_from_cityname(
        self, userinput: str, mirror: bool
    ) -> Tuple[str, str]:
        matching = []  # type: List[Tuple[str, str, str]]
        for (name, original_id, mirror_id) in self.bodies:
            if userinput.casefold() in name.casefold():
                # The oparl mirror doesn't give us the system id we need
                response = requests.get(original_id)
                response.raise_for_status()
                system_id = response.json()["system"]
                if mirror:
                    matching.append((name, system_id, mirror_id))
                else:
                    matching.append((name, system_id, original_id))
        if len(matching) == 0:
            raise RuntimeError("Could not find anything for '{}'".format(userinput))
        if len(matching) > 1:
            exact_matches = [
                i for i in matching if i[0].casefold() == userinput.casefold()
            ]
            if len(exact_matches) == 1:
                matching = exact_matches
            else:
                import json

                logger.warning(
                    "Found those entries: {}".format(json.dumps(matching, indent=4))
                )
                raise RuntimeError(
                    (
                        "There are {} matches and {} exact matchs for '{}' and I can't decide which one to use. "
                        + "Please provide a url yourself."
                    ).format(len(matching), len(exact_matches), userinput)
                )
        return matching[0][1:3]
