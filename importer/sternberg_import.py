import hashlib
import json
import logging
import os

import gi
import requests
from requests import HTTPError

from mainapp.models import File
from .oparl_import import OParlImport

gi.require_version("OParl", '0.4')
from gi.repository import OParl


class SternbergImport(OParlImport):
    """ Class for patching up the failures in Sternberg OParl """

    def resolve(self, _, url: str):
        response = super().resolve(_, url)
        if not response.get_success():
            return response

        if "/body" in url:
            oparl_list = json.loads(response.get_resolved_data())

            # Add missing "type"-attributes in body-lists
            if "data" in oparl_list:
                for oparl_object in oparl_list["data"]:
                    if "location" in oparl_object.keys() and isinstance(oparl_object["location"], dict):
                        oparl_object["location"]["type"] = "https://schema.oparl.org/1.0/Location"

            # Add missing "type"-attributes in single bodies
            if "location" in oparl_list.keys() and isinstance(oparl_list["location"], dict):
                oparl_list["location"]["type"] = "https://schema.oparl.org/1.0/Location"

            # Location in Person must be a url, not an object
            if "/person" in url and "data" in oparl_list:
                for oparl_object in oparl_list["data"]:
                    if "location" in oparl_object and isinstance(oparl_object["location"], dict):
                        oparl_object["location"] = oparl_object["location"]["id"]

            response = OParl.ResolveUrlResult(resolved_data=json.dumps(oparl_list), success=True,
                                              status_code=response.get_status_code())

        if "/membership" in url:
            oparl_list = json.loads(response.get_resolved_data())

            # If an array is returned instead of an object, we just skip all list entries except for the last one
            if isinstance(oparl_list, list):
                oparl_list = oparl_list[0]

            response = OParl.ResolveUrlResult(resolved_data=json.dumps(oparl_list), success=True,
                                              status_code=response.get_status_code())

        if "/person" in url:
            oparl_object = json.loads(response.get_resolved_data())
            if "location" in oparl_object and not isinstance(oparl_object["location"], str):
                oparl_object["location"] = oparl_object["location"]["id"]

            response = OParl.ResolveUrlResult(resolved_data=json.dumps(oparl_object), success=True,
                                              status_code=response.get_status_code())

        if "/meeting" in url:
            oparl_object = json.loads(response.get_resolved_data())
            if "location" in oparl_object and not isinstance(oparl_object["location"], str):
                oparl_object["location"]["type"] = "https://schema.oparl.org/1.0/Location"

            response = OParl.ResolveUrlResult(resolved_data=json.dumps(oparl_object), success=True,
                                              status_code=response.get_status_code())

        return response

    def download_file(self, file: File, libobject: OParl.File):
        """ Fix the invalid urls of sternberg oparl """
        url = libobject.get_download_url().replace(r"files//rim", r"files/rim")
        last_modified = self.glib_datetime_to_python(libobject.get_modified())

        if file.filesize and file.filesize > 0 and file.modified and last_modified and last_modified < file.modified:
            self.logger.info("Skipping cached Download: {}".format(url))
            return

        logging.info("Downloading {}".format(url))

        urlhash = hashlib.sha1(libobject.get_id().encode("utf-8")).hexdigest()
        path = os.path.join(self.storagefolder, urlhash)

        r = requests.get(url, allow_redirects=True)
        try:
            r.raise_for_status()
        except HTTPError as err:
            self.logger.error(err)
            file.storage_filename = "Error downloading File"
            file.filesize = -1
            return

        open(path, 'wb').write(r.content)

        file.filesize = os.stat(path).st_size
        file.storage_filename = urlhash
