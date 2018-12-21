import logging
from typing import Tuple, List, Any, TYPE_CHECKING

import requests
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from importer import CityToAGS
from importer.citytools import import_streets, import_outline
from importer.functions import get_importer
from importer.oparl_helper import default_options
from meine_stadt_transparent import settings

if TYPE_CHECKING:
    from importer.oparl_import import OParlImport

logger = logging.getLogger(__name__)


class OParlCli:
    """ Tries to import all required data (oparl system id, ags and city name for osm) from a user input
    that might be the name of a city, the url of a body or the url of a system.

    It uses the joint information the oparl dev portal and the oparl mirror.
    """

    def __init__(self):
        self.bodies = []  # type: List[Tuple[str, str, str]]

        response = requests.get(settings.OPARL_ENDPOINTS_LIST)
        response.raise_for_status()
        next_page = settings.OPARL_ENDPOINTS_LIST
        while next_page:
            response = requests.get(next_page).json()
            next_page = response["links"].get("next")
            for body in response["data"]:
                self.bodies.append(
                    (
                        body.get("name") or body["oparl-mirror:originalId"],
                        body["oparl-mirror:originalId"],
                        body["id"],
                    )
                )

    def from_userinput(self, userinput: str, mirror: bool) -> None:
        try:
            URLValidator()(userinput)
            is_url = True
        except ValidationError:
            is_url = False

        if not is_url:
            endpoint_system, endpoint_body = self.get_endpoint_from_cityname(
                userinput, mirror
            )
        else:
            endpoint_system, endpoint_body = self.get_endpoint_from_body_url(userinput)

        importer, liboparl_body = self.get_importer_with_body(
            endpoint_body, endpoint_system
        )

        ags = self.get_ags(liboparl_body, userinput)

        self.run_importer(ags, importer, liboparl_body)

    def get_endpoint_from_body_url(self, userinput: str) -> Tuple[str, str]:
        # We can't use the resolver here as we don't know the system url yet, which the resolver needs for determining
        # the cache folder
        logging.info("Using {} as url".format(userinput))
        response = requests.get(userinput)
        response.raise_for_status()
        data = response.json()
        if data.get("type") != "https://schema.oparl.org/1.0/Body":
            raise Exception("The url you provided didn't point to an oparl body")
        endpoint_system = data["system"]
        endpoint_id = userinput
        return endpoint_system, endpoint_id

    def get_importer_with_body(
        self, endpoint_body: str, endpoint_system: str
    ) -> Tuple["OParlImport", Any]:
        """ Get the oparl importer and the body as liboparl object """
        liboparl_body = None
        options = default_options.copy()

        options["entrypoint"] = endpoint_system
        importer = get_importer(options)
        bodies = importer.get_bodies()
        for body in bodies:
            if body.get_id() == endpoint_body:
                liboparl_body = body
                break
        if not liboparl_body:
            raise Exception(
                "Failed to find body {} in {}".format(endpoint_body, endpoint_system)
            )
        return importer, liboparl_body

    def run_importer(
        self, ags: str, importer: "OParlImport", liboparl_body: Any
    ) -> None:
        logger.info("Importing {}".format(liboparl_body.get_id()))
        logger.info("The Amtliche Gemeindeschlüssel is {}".format(ags))
        main_body = importer.body(liboparl_body)

        dotenv = ""

        if importer.entrypoint != settings.OPARL_ENDPOINT:
            dotenv += "OPARL_ENDPOINT={}\n".format(importer.entrypoint)

        if main_body.id != settings.SITE_DEFAULT_BODY:
            dotenv += "SITE_DEFAULT_BODY={}\n".format(main_body.id)

        if dotenv:
            logger.info(
                "Found the oparl endpoint. Please add the following line to your dotenv file "
                "(you'll be reminded again after the import finished): \n\n" + dotenv
            )

        logger.info("Importing the shape of the city")
        import_outline(main_body, ags)
        logger.info("Importing the streets")
        import_streets(main_body, ags)

        logger.info("Importing the papers")
        importer.list_batched(liboparl_body.get_paper, importer.paper)
        logger.info("Importing the persons")
        importer.list_batched(liboparl_body.get_person, importer.person)
        logger.info("Importing the organizations")
        importer.list_batched(liboparl_body.get_organization, importer.organization)
        logger.info("Importing the meetings")
        importer.list_batched(liboparl_body.get_meeting, importer.meeting)

        logger.info("Add some missing foreign keys")
        importer.add_missing_associations()

        if dotenv:
            logger.info(
                "Done! Please add the following line to your dotenv file: \n\n"
                + dotenv
                + "\n"
            )

    def get_ags(self, liboparl_body: Any, userinput: str) -> str:
        ags = liboparl_body.get_ags()
        if not ags:
            ags = CityToAGS.query_wikidata(userinput)
        if len(ags) == 0:
            raise Exception(
                "Could not find the Gemeindeschlüssel for '{}'".format(userinput)
            )
        if len(ags) > 1:
            raise Exception(
                "Found more than one Gemeindeschlüssel for '{}': {}".format(
                    userinput, ags
                )
            )

        logging.info("Using {} as Gemeindeschlüssel for '{}'".format(ags, userinput))
        return ags[0][1]

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
            raise Exception("Could not find anything for '{}'".format(userinput))
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
                        "There are {} matches and {} exact matchs for {} and I can't decide which one to use. "
                        + "Please provide a url yourself."
                    ).format(len(matching), len(exact_matches), userinput)
                )
        return matching[0][1:3]
