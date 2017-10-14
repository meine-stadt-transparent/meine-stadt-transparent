import json

from .oparl_importer import OParlImporter


class SternbergImport(OParlImporter):
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
                    if "location" in oparl_object.keys() and not isinstance(oparl_object["location"], str):
                        oparl_object["location"]["type"] = "https://schema.oparl.org/1.0/Location"

            # Add missing "type"-attributes in single bodies
            if "location" in oparl_list.keys() and not isinstance(oparl_list["location"], str):
                oparl_list["location"]["type"] = "https://schema.oparl.org/1.0/Location"

            response.set_resolved_data(json.dumps(oparl_list))

        if "/membership" in url:
            oparl_list = json.loads(response.get_resolved_data())

            # If an array is resturned instead of an object, we just skip all list entries except for the last one
            if isinstance(oparl_list, list):
                oparl_list = oparl_list[0]

            response.set_resolved_data(json.dumps(oparl_list))

        return response

