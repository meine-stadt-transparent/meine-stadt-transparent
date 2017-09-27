import json

from .oparl_importer import OParlImporter


class SternbergImport(OParlImporter):
    """ Class for patching up the failures in Sternberg OParl """

    def resolve(self, _, url: str):
        response = super().resolve(_, url)
        if response.get_success() and "/body" in url:
            oparl_list = json.loads(response.get_resolved_data())
            for oparl_object in oparl_list["data"]:
                if "location" in oparl_object.keys() and type(oparl_object["location"]) != str:
                    oparl_object["location"]["type"] = "https://schema.oparl.org/1.0/Location"
            response.set_resolved_data(json.dumps(oparl_list))
        return response
