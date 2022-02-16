import json
import logging
import re
from typing import Tuple, List, Optional

from django import db
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from importer import JSON
from importer.functions import requests_get
from importer.importer import Importer
from importer.loader import get_loader_from_system
from importer.utils import Utils
from mainapp.functions.city_to_ags import city_to_ags
from mainapp.functions.citytools import import_outline, import_streets
from mainapp.models import Body
from meine_stadt_transparent import settings

logger = logging.getLogger(__name__)


class Cli:
    """Tries to import all required data (oparl system id, ags and city name for osm) from a user input
    that might be the name of a city, the url of a body or the url of a system.

    It uses the information from wikidata, open street map and the oparl mirror.
    """

    def __init__(self):
        self.index = []  # type: List[Tuple[str, str, str]]
        self.utils = Utils()

    def load_index(self) -> List[Tuple[str, str, str]]:
        """ " Loads the list of known endpoints from the oparl mirror if it has not been loaded yet"""
        if self.index:
            return self.index
        next_page = settings.OPARL_INDEX
        while next_page:
            response = requests_get(next_page)
            data = response.json()
            next_page = data["links"].get("next")
            for body in data["data"]:
                if "oparl-mirror:originalId" not in body:
                    continue
                self.index.append(
                    (
                        body.get("name") or body["oparl-mirror:originalId"],
                        body["oparl-mirror:originalId"],
                        body["id"],
                    )
                )

        return self.index

    def from_userinput(
        self,
        userinput: str,
        mirror: bool,
        ags: Optional[str],
        skip_body_extra: bool = False,
        skip_files: bool = False,
    ) -> None:
        body_id, entrypoint = self.get_entrypoint_and_body(userinput, mirror)
        importer = Importer(get_loader_from_system(entrypoint))
        body_data, dotenv = self.import_body_and_metadata(
            body_id, importer, userinput, ags, skip_body_extra
        )

        logger.info("Loading the bulk data from the oparl api")
        importer.fetch_lists_initial([body_data])

        # Also avoid "MySQL server has gone away" errors due to timeouts
        # https://stackoverflow.com/a/32720475/3549270
        db.close_old_connections()

        logger.info("Loading the data into the database")
        importer.import_objects()

        if not skip_files:
            logger.info("Loading the files")
            importer.load_files(
                fallback_city=settings.GEOEXTRACT_SEARCH_CITY or userinput
            )

        if dotenv:
            logger.info(
                f"Done! Please add the following line to your dotenv file: \n\n{dotenv}\n"
            )

    def import_body_and_metadata(
        self,
        body_id: str,
        importer: Importer,
        userinput: str,
        ags: Optional[str],
        skip_body_extra: bool = False,
    ) -> Tuple[JSON, str]:
        logger.info(f"Fetching the body {body_id}")
        [body_data] = importer.load_bodies(body_id)
        logger.info("Importing the body")
        [body] = importer.import_bodies()
        importer.converter.default_body = body
        logger.info("Looking up the Amtliche Gemeindeschlüssel")
        if ags:
            if len(ags) != 5 and len(ags) != 8:
                logger.warning(
                    "Your Amtlicher Gemeindeschlüssel has {} digits instead of 5 or 8".format(
                        len(ags)
                    )
                )
            body.ags = ags
        else:
            ags, match_name = self.get_ags(body, importer.loader.system, userinput)
            body.ags = ags
            # Sometimes there's a bad short name (e.g. "Rat" for Erkelenz),
            # so we use the name that's in wikidata instead
            body.short_name = match_name
        body.save()
        logger.info(
            "Using {} as Amtliche Gemeindeschlüssel for '{}'".format(
                body.ags, body.short_name
            )
        )
        dotenv = ""
        if body.id != settings.SITE_DEFAULT_BODY:
            dotenv += f"SITE_DEFAULT_BODY={body.id}\n"
        if dotenv:
            logger.info(
                "Found the oparl endpoint. Please add the following line to your dotenv file "
                "(you'll be reminded again after the import finished): \n\n" + dotenv
            )

        if not skip_body_extra:
            logger.info("Importing the shape of the city")
            import_outline(body)
            logger.info("Importing the streets")
            import_streets(body)
            logger.info(f"Body {body.short_name} import with geo data successful.")
        else:
            logger.info(
                f"Body {body.short_name} import successful. "
                f"Don't forget to run import_streets, import_amenities and import_outline"
            )
        return body_data.data, dotenv

    def get_entrypoint_and_body(
        self, userinput: str, mirror: bool = False
    ) -> Tuple[str, str]:
        try:
            URLValidator()(userinput)
            is_url = True
        except ValidationError:
            is_url = False
        if not is_url:
            entrypoint, body_id = self.get_endpoint_from_cityname(userinput, mirror)
        else:
            entrypoint, body_id = self.get_endpoint_from_body_url(userinput)

        logger.info(f"Your body id is {body_id} and your system id is {entrypoint}")

        return body_id, entrypoint

    def get_endpoint_from_body_url(self, userinput: str) -> Tuple[str, str]:
        # We can't use the resolver here as we don't know the system url yet, which the resolver needs for determining
        # the cache folder
        logging.info(f"Using {userinput} as url")
        response = requests_get(userinput)
        data = response.json()
        if data.get("type") not in [
            "https://schema.oparl.org/1.0/Body",
            "https://schema.oparl.org/1.1/Body",
        ]:
            raise RuntimeError("The url you provided didn't point to an oparl body")
        endpoint_system = data["system"]
        endpoint_id = data["id"]
        if userinput != endpoint_id:
            logger.warning(
                f"The body's url '{userinput}' doesn't match the body's id '{endpoint_id}'"
            )
        return endpoint_system, endpoint_id

    def get_ags(self, body: Body, system: JSON, userinput: str) -> Tuple[str, str]:
        """
        This function tries:
         1. The ags field in the oparl body
         2. Querying wikidata with
            a) the body's short name
            b) the user's input
            c) the body's full name
            d) the system's name
            e) locality in the location

        Returns the ags and the name that did match
        """
        ags = body.ags
        if ags:
            if len(ags) == 8 or len(ags) == 5:
                return ags, body.short_name
            else:
                logger.error(f"Ignoring ags '{ags}' with invalid length {len(ags)}")

        district = bool(re.match(settings.DISTRICT_REGEX, body.name, re.IGNORECASE))

        to_check = [
            ("body short name", body.short_name),
            ("user input", userinput),
            ("body name", body.name),
        ]

        if system.get("name"):
            short_system_name = self.utils.normalize_body_name(system["name"])
            to_check.append(("system name", short_system_name))

        if body.center and body.center.locality:
            locality = body.center.locality
            to_check.append(("body location locality", locality))

        for source, value in to_check:
            ags = city_to_ags(value, district)
            if ags:
                logger.debug(f"Found ags using the {source}: '{value}'")
                return ags, value

        raise RuntimeError(
            f"Could not determine the Amtliche Gemeindeschlüssel using {to_check}.\n"
            f"Set it manually using `--ags`"
        )

    def get_endpoint_from_cityname(
        self, userinput: str, mirror: bool
    ) -> Tuple[str, str]:
        matching = []  # type: List[Tuple[str, str, str]]
        for (name, original_id, mirror_id) in self.load_index():
            if userinput.casefold() in name.casefold():
                # The oparl mirror doesn't give us the system id we need
                response = requests_get(original_id)
                system_id = response.json()["system"]
                if mirror:
                    matching.append((name, system_id, mirror_id))
                else:
                    matching.append((name, system_id, original_id))
        if len(matching) == 0:
            raise RuntimeError(
                f"Could not find anything for '{userinput}'. "
                f"Please check that it is in the list under {settings.OPARL_INDEX} or provide the body id."
            )
        if len(matching) > 1:
            exact_matches = [
                i for i in matching if i[0].casefold() == userinput.casefold()
            ]
            if len(exact_matches) == 1:
                matching = exact_matches
            else:
                logger.warning(f"Found those entries: {json.dumps(matching, indent=4)}")
                raise RuntimeError(
                    f"There are {len(matching)} matches and {len(exact_matches)} exact matches for '{userinput}' and "
                    "I can't decide which one to use. Please provide a body url yourself."
                )
        return matching[0][1:3]
