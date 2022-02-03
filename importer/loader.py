import json
import logging
import re
import time
from json import JSONDecodeError

from typing import Optional, Tuple, Dict, Any

from requests import HTTPError, Response

from importer import JSON
from importer.functions import requests_get
from importer.models import CachedObject

logger = logging.getLogger(__name__)


class BaseLoader:
    """Provides a json and file download function.

    This class can be overwritten for vendor specific fixups
    """

    def __init__(self, system: JSON) -> None:
        self.system = system

    def load(self, url: str, query: Optional[Dict[str, str]] = None) -> JSON:
        logger.debug(f"Loader is loading {url}")
        if query is None:
            query = dict()
        response = requests_get(url, params=query)
        data = response.json()
        if data is None:  # json() can actually return None
            data = dict()
        if "id" in data and data["id"] != url:
            logger.warning(f"Mismatch between url and id. url: {url} id: {data['id']}")
        return data

    def load_file(self, url: str) -> Tuple[bytes, Optional[str]]:
        """Returns the content and the content type"""
        response = requests_get(url)
        content = response.content
        content_type = response.headers.get("Content-Type")
        return content, content_type


class SternbergLoader(BaseLoader):
    empty_list_error = {
        "error": "Die angeforderte Ressource wurde nicht gefunden.",
        "code": 802,
        "type": "SD.NET RIM Webservice",
    }

    empty_page = {"data": [], "links": {}, "pagination": {}}

    def visit_object(self, response: JSON):
        if response.get("type") == "https://schema.oparl.org/1.0/File":
            if "accessUrl" in response:
                response["accessUrl"] = response["accessUrl"].replace(
                    r"files//rim", r"files/rim"
                )
            if "downloadUrl" in response:
                response["downloadUrl"] = response["downloadUrl"].replace(
                    r"files//rim", r"files/rim"
                )

        if response.get("type") == "https://schema.oparl.org/1.0/Body":
            # Check for a missing leading zero
            ags = response.get("ags")
            if ags and len(ags) == 7:
                # noinspection PyTypeChecker
                response["ags"] = "0" + ags

    def load(self, url: str, query: Optional[Dict[str, str]] = None) -> JSON:
        if query is None:
            query = dict()

        try:
            response = super().load(url, query)  # type: Dict[str, Any]
        except HTTPError as error:
            # Sometimes, an error is returned when the list would have been empty
            if (
                error.response.status_code == 404
                and "modified_since" in query
                and error.response.json() == self.empty_list_error
            ):
                response = self.empty_page
            else:
                raise error

        # Sometime, an empty list is returned instead of an object with an empty list
        if "modified_since" in query and response == []:
            response = self.empty_page

        if response.get("deleted", False) and "type" not in response:
            response["type"] = (
                "https://schema.oparl.org/1.0/" + url.split("/")[-2].title()
            )

        # Instead of the body list, there's only a body
        # https://ris.krefeld.de/webservice/oparl/v1.0/body
        if url.endswith("/body") and "id" in response:
            response = {"data": [response], "pagination": {}, "links": {}}

        if "/body" in url:
            # Add missing "type"-attributes in body-lists
            if "data" in response:
                for data in response["data"]:
                    if "location" in data.keys() and isinstance(data["location"], dict):
                        data["location"][
                            "type"
                        ] = "https://schema.oparl.org/1.0/Location"

                # There are deleted entries in unfiltered external lists (which they shouldn't) and then
                # they don't even have type attributes (which are mandatory)
                for entry in response["data"][:]:
                    if entry.get("deleted") and "type" not in entry:
                        response["data"].remove(entry)

            # Add missing "type"-attributes in single bodies
            if "location" in response.keys() and isinstance(response["location"], dict):
                response["location"]["type"] = "https://schema.oparl.org/1.0/Location"

            # Location in Person must be a url, not an object
            if "/person" in url and "data" in response:
                for data in response["data"]:
                    if "location" in data and isinstance(data["location"], dict):
                        data["location"] = data["location"]["id"]

            if "/organization" in url and "data" in response:
                for data in response["data"]:
                    if "id" in data and "type" not in data:
                        data["type"] = "https://schema.oparl.org/1.0/Organization"

        if "/membership" in url:
            # If an array is returned instead of an object, we just skip all list entries except for the last one
            if isinstance(response, list):
                response = response[0]

        if "/person" in url:
            if "location" in response and not isinstance(response["location"], str):
                response["location"] = response["location"]["id"]

        if "/meeting" in url:
            if "location" in response and not isinstance(response["location"], str):
                response["location"]["type"] = "https://schema.oparl.org/1.0/Location"

        if "data" in response:
            for data in response["data"]:
                self.visit_object(data)
        else:
            self.visit_object(response)

        return response

    def load_file(self, url: str) -> Tuple[bytes, Optional[str]]:
        try:
            content, content_type = super().load_file(url)
        except HTTPError as error:
            # Sometimes (if there's a dot in the filename(?)), the extension gets overriden
            # by repeating the part after the dot in the extension-less filename
            splitted = error.response.url.split(".")
            if (
                error.response.status_code == 404
                and len(splitted) > 2
                and splitted[-2] == splitted[-1]
            ):
                new_url = ".".join(splitted[:-1]) + ".pdf"
                content, content_type = super().load_file(new_url)
            else:
                raise error
        if content_type == "application/octetstream; charset=UTF-8":
            content_type = None
        return content, content_type


class CCEgovLoader(BaseLoader):
    def visit(self, data: JSON):
        """Removes quirks like `"streetAddress": " "` in Location"""
        # `"auxiliaryFile": { ... }` -> `"auxiliaryFile": [{ ... }]`
        if "auxiliaryFile" in data and isinstance(data["auxiliaryFile"], dict):
            logger.warning(
                f"auxiliaryFile is supposed to be an array of objects, "
                f"but is an object (in {data.get('id')})"
            )
            data["auxiliaryFile"] = [data["auxiliaryFile"]]
        for key, value in data.copy().items():
            if isinstance(value, dict):
                self.visit(value)
            if isinstance(value, list):
                for i in value:
                    if isinstance(i, dict):
                        self.visit(i)
            elif isinstance(value, str):
                if value == "N/A" or not value.strip():
                    del data[key]

    def load(self, url: str, query: Optional[dict] = None) -> JSON:
        logger.debug(f"Loader is loading {url}")
        if query is None:
            query = dict()

        try:
            response = requests_get(url, params=query)
        except HTTPError as e:
            if e.response.status_code == 500:
                logger.error(f"Got an 500 for a CC e-gov request, retrying: {e}")
                response = requests_get(url, params=query)
            else:
                raise
        text = response.text
        try:
            data = json.loads(text)
        except JSONDecodeError:
            logger.error(
                f"The server returned invalid json. This is a bug in the OParl implementation: {url}"
            )
            # Hack with based on std json code to load broken json where the control characters (U+0000 through
            # U+001F except \n) weren't properly escaped
            ESCAPE = re.compile(r"[\x00-\x09\x0B-\x1f]")
            ESCAPE_DCT = {}
            for i in range(0x20):
                ESCAPE_DCT.setdefault(chr(i), "\\u{0:04x}".format(i))

            def replace(match):
                return ESCAPE_DCT[match.group(0)]

            text = ESCAPE.sub(replace, text)
            data = json.loads(text)

        if data is None:  # json() can actually return None
            data = dict()
        if "id" in data and data["id"] != url:
            logger.warning(f"Mismatch between url and id. url: {url} id: {data['id']}")

        self.visit(data)
        return data

    def load_file(self, url: str) -> Tuple[bytes, Optional[str]]:
        """Returns the content and the content type"""
        response = requests_get(url)
        content = response.content
        content_type = response.headers.get("Content-Type")
        return content, content_type


class SomacosLoader(BaseLoader):
    max_retries: int = 3
    error_sleep_seconds: int = 5

    def get_with_retry_on_500(self, url: str) -> Response:
        """Custom retry logic with logging and backoff"""
        current_try = 1
        while True:
            try:
                return requests_get(url)
            except HTTPError as e:
                if e.response.status_code == 500:
                    if current_try == self.max_retries:
                        logger.error(
                            f"Request failed {self.max_retries} times with an Error 500, aborting: {e}"
                        )
                        raise
                    else:
                        logger.error(
                            f"Got an 500 for a Somacos request, "
                            f"retrying after sleeping {self.error_sleep_seconds}s: {e}"
                        )
                        time.sleep(self.error_sleep_seconds)
                        current_try += 1
                        continue
                else:
                    raise

    def load(self, url: str, query: Optional[Dict[str, str]] = None) -> JSON:
        if query:
            # Somacos doesn't like encoded urls
            url = (
                url
                + "?"
                + "&".join([key + "=" + value for key, value in query.items()])
            )
        logger.debug(f"Loader is loading {url}")
        response = self.get_with_retry_on_500(url)

        data = response.json()
        if "id" in data and data["id"] != url:
            logger.warning(f"Mismatch between url and id. url: {url} id: {data['id']}")
        return data


def get_loader_from_system(entrypoint: str) -> BaseLoader:
    response = requests_get(entrypoint)
    system = response.json()
    if system.get("contactName") == "STERNBERG Software GmbH & Co. KG":
        logger.info("Using Sternberg patches")
        return SternbergLoader(system)
    elif (
        system.get("vendor") == "http://cc-egov.de/"
        or system.get("vendor") == "https://www.cc-egov.de"
    ):
        logger.info("Using CC e-gov patches")
        return CCEgovLoader(system)
    elif (
        system.get("vendor") == "http://www.somacos.de"
        or system.get("product")
        == "Sitzungsmanagementsystem Session  Copyright SOMACOS GmbH & Co. KG"
    ):
        logger.info("Using Somacos patches ")
        return SomacosLoader(system)
    else:
        logger.info("Using no vendor specific patches")
        return BaseLoader(system)


def get_loader_from_body(body_id: str) -> BaseLoader:
    """
    Assumptions:
     * The body->system link hasn't changed
     * The system might have, e.g. to a newer version where we don't workarounds anymore
    """
    cached_body = CachedObject.objects.filter(url=body_id).first()
    if cached_body:
        logger.info(f"The body {body_id} is cached")
        system_id = cached_body.data["system"]
    else:
        logger.info(f"Fetching the body {body_id}")
        response = requests_get(body_id)
        data = response.json()
        CachedObject.objects.create(
            url=data["id"], oparl_type=data["type"], data=data, to_import=False
        )
        system_id = data["system"]

    return get_loader_from_system(system_id)
