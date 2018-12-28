from typing import Dict, Any

import requests

from importer.oparl_import import OParlImport
from importer.oparl_utils import OParlUtils
from importer.sternberg_import import SternbergUtils


def get_importer(options: Dict[str, Any]) -> OParlImport:
    """ Queries the system object to determine the vendor and the necessary workarounds. """

    response = requests.get(options["entrypoint"])
    response.raise_for_status()
    system = response.json()

    # This will likely need a more sophisticated logic in te future
    if system.get("contactName") == "STERNBERG Software GmbH & Co. KG":
        utils = OParlUtils(options)
    else:
        utils = SternbergUtils(options)

    return OParlImport(utils)
