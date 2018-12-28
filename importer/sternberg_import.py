from typing import Optional, Dict, Any

from importer.oparl_helper import ResolveUrlResult
from mainapp.models import File
from .oparl_import import OParlImport


class SternbergImport(OParlImport):
    def resolve(self, url: str) -> ResolveUrlResult:
        response = super(SternbergImport, self).resolve(url)
        if not response.success:
            return response

        if "/body" in url:
            oparl_list = response.resolved_data

            # Add missing "type"-attributes in body-lists
            if "data" in oparl_list:
                for oparl_object in oparl_list["data"]:
                    if "location" in oparl_object.keys() and isinstance(
                        oparl_object["location"], dict
                    ):
                        oparl_object["location"][
                            "type"
                        ] = "https://schema.oparl.org/1.0/Location"

            # Add missing "type"-attributes in single bodies
            if "location" in oparl_list.keys() and isinstance(
                oparl_list["location"], dict
            ):
                oparl_list["location"]["type"] = "https://schema.oparl.org/1.0/Location"

            # Location in Person must be a url, not an object
            if "/person" in url and "data" in oparl_list:
                for oparl_object in oparl_list["data"]:
                    if "location" in oparl_object and isinstance(
                        oparl_object["location"], dict
                    ):
                        oparl_object["location"] = oparl_object["location"]["id"]

            if "/organization" in url and "data" in oparl_list:
                for oparl_object in oparl_list["data"]:
                    if "id" in oparl_object and "type" not in oparl_object:
                        oparl_object[
                            "type"
                        ] = "https://schema.oparl.org/1.0/Organization"

            response = ResolveUrlResult(
                resolved_data=oparl_list, success=True, status_code=response.status_code
            )

        if "/membership" in url:
            oparl_list = response.resolved_data

            # If an array is returned instead of an object, we just skip all list entries except for the last one
            if isinstance(oparl_list, list):
                oparl_list = oparl_list[0]

            response = ResolveUrlResult(
                resolved_data=oparl_list, success=True, status_code=response.status_code
            )

        if "/person" in url:
            oparl_object = response.resolved_data
            if "location" in oparl_object and not isinstance(
                oparl_object["location"], str
            ):
                oparl_object["location"] = oparl_object["location"]["id"]

            response = ResolveUrlResult(
                resolved_data=oparl_object,
                success=True,
                status_code=response.status_code,
            )

        if "/meeting" in url:
            oparl_object = response.resolved_data
            if "location" in oparl_object and not isinstance(
                oparl_object["location"], str
            ):
                oparl_object["location"][
                    "type"
                ] = "https://schema.oparl.org/1.0/Location"

            response = ResolveUrlResult(
                resolved_data=oparl_object,
                success=True,
                status_code=response.status_code,
            )

        return response

    def download_file(
        self, file: File, url: str, libobject: Dict[str, Any]
    ) -> Optional[bytes]:
        """ Fix the invalid urls of sternberg oparl """
        url = url.replace(r"files//rim", r"files/rim")
        return super().download_file(file, url, libobject)
