import logging
from typing import Optional, Tuple

import requests

from importer import JSON
from importer.models import CachedObject

logger = logging.getLogger(__name__)


class BaseLoader:
    """ Provides a json and file download function.

    This class can be overwritten for vendor specific fixups
    """

    def __init__(self, system: JSON) -> None:
        self.system = system

    def load(self, url: str, query: Optional[dict] = None) -> JSON:
        logger.debug("Loader is loading {}".format(url))
        if query is None:
            query = dict()
        response = requests.get(url, params=query)
        response.raise_for_status()
        return response.json()

    def load_file(self, url: str) -> Tuple[bytes, str]:
        response = requests.get(url)
        response.raise_for_status()
        content = response.content
        content_type = response.headers.get("Content-Type")
        return content, content_type


class SternbergLoader(BaseLoader):
    def load(self, url: str, query: Optional[dict] = None) -> JSON:
        response = super(SternbergLoader, self).load(url, query)

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
                    if entry.get("deleted") and not "type" in entry:
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

        if response.get("type") == "https://schema.oparl.org/1.0/File":
            if "accessUrl" in response:
                response["accessUrl"] = response["accessUrl"].replace(
                    r"files//rim", r"files/rim"
                )
            if "downloadUrl" in response:
                response["downloadUrl"] = response["downloadUrl"].replace(
                    r"files//rim", r"files/rim"
                )

        return response


class CCEgovLoader(BaseLoader):
    def visit(self, data: JSON):
        """ Removes quirks like `"streetAddress": " "` in Location """
        for key, value in data.copy().items():
            if isinstance(value, dict):
                self.visit(value)
            elif isinstance(value, str):
                if value == "N/A" or not value.strip():
                    del data[key]

    def load(self, url: str, query: Optional[dict] = None) -> JSON:
        response = super(CCEgovLoader, self).load(url, query)
        self.visit(response)
        return response


def get_loader_from_system(entrypoint: str) -> BaseLoader:
    system = requests.get(entrypoint).json()
    if system.get("contactName") == "STERNBERG Software GmbH & Co. KG":
        return SternbergLoader(system)
    if system.get("vendor") == "http://cc-egov.de/":
        return CCEgovLoader(system)
    return BaseLoader(system)


def get_loader_from_body(body_id: str) -> BaseLoader:
    """
    Assumptions:
     * The body->system link hasn't changed
     * The system might have, e.g. to a newer version where we don't workarounds anymore
    """
    cached_body = CachedObject.objects.filter(url=body_id).first()
    if cached_body:
        logger.info("The body {} is cached".format(body_id))
        system_id = cached_body.data["system"]
    else:
        logger.info("Fetching the body {}".format(body_id))
        response = requests.get(body_id)
        response.raise_for_status()
        data = response.json()
        CachedObject.objects.create(
            url=data["id"], oparl_type=data["type"], data=data, to_import=False
        )
        system_id = data["system"]

    return get_loader_from_system(system_id)
