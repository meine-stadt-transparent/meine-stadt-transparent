from typing import Dict, Any

from django.urls import reverse
from django.utils.translation import pgettext

from mainapp.functions.geo_functions import latlng_to_address
from mainapp.functions.search import (
    NotificationSearchResult,
    params_to_search_string,
    DOCUMENT_TYPE_NAMES,
    DOCUMENT_TYPE_NAMES_PL,
)
from mainapp.models import Person, Organization
from meine_stadt_transparent.settings import ABSOLUTE_URI_BASE


def params_are_subscribable(params: Dict[str, Any]) -> bool:
    if "after" in params:
        return False
    if "before" in params:
        return False
    return True


def search_result_for_notification(result: Dict[str, Any]) -> NotificationSearchResult:
    if result["type"] == "meeting":
        title = result["name"]
        url = ABSOLUTE_URI_BASE + reverse("meeting", args=[result["id"]])
    elif result["type"] == "paper":
        title = result["name"]
        url = ABSOLUTE_URI_BASE + reverse("paper", args=[result["id"]])
    elif result["type"] == "file":  # filename?
        title = result["name"]
        url = ABSOLUTE_URI_BASE + reverse("file", args=[result["id"]])
    else:
        title = "Unknown"
        url = ""

    return NotificationSearchResult(
        title,
        url,
        result["type"],
        DOCUMENT_TYPE_NAMES[result["type"]],
        result["highlight"],
    )


def params_to_human_string(params: Dict[str, Any]) -> str:
    if "document-type" in params:
        split = params["document-type"].split(",")
        what = []
        for el in split:
            what.append(DOCUMENT_TYPE_NAMES_PL[el])
        if len(what) > 1:
            last_el = what.pop()
            description = ", ".join(what)
            description += " " + pgettext("Search query", "and") + " " + last_el
        else:
            description = what[0]

    else:
        description = pgettext("Search query", "Documents")

    strs = []

    if "searchterm" in params and params["searchterm"] != "":
        strs.append(
            pgettext("Search query", 'containing "%STR%"').replace(
                "%STR%", params["searchterm"]
            )
        )

    if "person" in params:
        person = Person.objects.get(pk=params["person"])
        if person:
            strs.append(
                pgettext("Search query", "mentioning %FROM%").replace(
                    "%FROM%", str(person)
                )
            )

    if "organization" in params:
        organization = Organization.objects.get(pk=params["organization"])
        if organization:
            strs.append(
                pgettext("Search query", "assigned to %TO%").replace(
                    "%TO%", str(organization)
                )
            )

    if "radius" in params:
        place_name = latlng_to_address(params["lat"], params["lng"])
        locstr = pgettext(
            "Search query", 'with a location within %DISTANCE%m around "%PLACE%"'
        )
        strs.append(
            locstr.replace("%DISTANCE%", params["radius"]).replace(
                "%PLACE%", place_name
            )
        )

    if "before" in params and "after" in params:
        strs.append(
            pgettext("Search query", "published from %FROM% to %TO%")
            .replace("%FROM%", params["after"])
            .replace("%TO%", params["before"])
        )
    elif "before" in params:
        strs.append(
            pgettext("Search query", "published before %TO%").replace(
                "%TO%", params["before"]
            )
        )
    elif "after" in params:
        strs.append(
            pgettext("Search query", "published after %FROM%").replace(
                "%FROM%", params["after"]
            )
        )

    if len(strs) > 0:
        description += " " + ", ".join(strs)

    return description


def params_are_equal(params1: dict, params2: dict) -> bool:
    # Comparison should be case-insensitive, as you usually don't subscribe to "school" and "School" at the same time
    return (
        params_to_search_string(params1).lower()
        == params_to_search_string(params2).lower()
    )
