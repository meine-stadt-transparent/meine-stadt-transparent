import logging
import re
from typing import Optional, Dict, Any

from django.conf import settings
from geopy import OpenCage, Nominatim
from geopy.exc import GeocoderServiceError
from slugify import slugify

logger = logging.getLogger(__name__)


def get_geolocator(fallback=False):
    if settings.GEOEXTRACT_ENGINE.lower() == "opencage" and not fallback:
        if not settings.OPENCAGE_KEY:
            raise ValueError(
                "OpenCage Data is selected as Geocoder, however no OPENCAGE_KEY is set"
            )
        geolocator = OpenCage(settings.OPENCAGE_KEY)
    else:
        geolocator = Nominatim(user_agent=slugify(settings.PRODUCT_NAME) + "/1.0")

    return geolocator


def geocode(search: str) -> Optional[Dict[str, Any]]:
    try:
        location = get_geolocator().geocode(
            search, language=settings.GEOEXTRACT_LANGUAGE, exactly_one=False
        )
    except GeocoderServiceError as e:
        logger.warning(e)
        try:
            location = get_geolocator(fallback=True).geocode(
                search, language=settings.GEOEXTRACT_LANGUAGE, exactly_one=False
            )
        except GeocoderServiceError:
            logger.exception(
                "Geocoder fallback service failed. Search string was {}".format(search)
            )
            return None

    if not location:
        return None

    return {
        "type": "Point",
        "coordinates": [location[0].longitude, location[0].latitude],
    }


def _format_opencage_location(location):
    components = location.raw["components"]
    if "road" in components:
        address = components["road"]
        if "house_number" in components:
            address += " " + components["house_number"]
    elif "pedestrian" in components:
        address = components["pedestrian"]
    else:
        address = location.address
    return address


def _format_nominatim_location(location):
    if re.match("^\d", location.split(",")[0]):
        # Number at the beginning: probably a house number
        return location.split(",")[1] + " " + location.split(",")[0]
    else:
        return location.split(",")[0]


def latlng_to_address(lat, lng):
    geolocator = get_geolocator()
    location = geolocator.reverse(str(lat) + ", " + str(lng))
    if len(location) > 0:
        if settings.GEOEXTRACT_ENGINE.lower() == "opencage":
            return _format_opencage_location(location[0])
        else:
            return _format_nominatim_location(location[0])
    else:
        return str(lat) + ", " + str(lng)
