import logging
import re
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse

from django.conf import settings
from geopy import OpenCage, Nominatim, MapBox
from geopy.exc import GeocoderServiceError
from geopy.geocoders.base import Geocoder
from slugify import slugify

logger = logging.getLogger(__name__)


def get_geolocators() -> List[Tuple[str, Geocoder]]:
    geolocators = []
    if settings.GEOEXTRACT_ENGINE == "opencage":
        if not settings.OPENCAGE_KEY:
            raise ValueError(
                "OpenCage Data is selected as Geocoder, however no OPENCAGE_KEY is set"
            )
        geolocators.append(("opencage", OpenCage(settings.OPENCAGE_KEY)))
    if settings.MAPBOX_TOKEN:
        geolocators.append(("mapbox", MapBox(settings.MAPBOX_TOKEN)))
    nominatim_url = urlparse(settings.NOMINATIM_URL)
    geolocators.append(
        (
            "nominatim",
            Nominatim(
                user_agent=slugify(settings.PRODUCT_NAME) + "/1.0",
                domain=nominatim_url.netloc,
                scheme=nominatim_url.scheme,
            ),
        )
    )

    return geolocators


def geocode(search: str) -> Optional[Dict[str, Any]]:
    for name, geolocator in get_geolocators():
        try:
            if name == "mapbox":
                location = geolocator.geocode(search, exactly_one=False)
            else:
                # noinspection PyArgumentList
                location = geolocator.geocode(
                    search, language=settings.GEOEXTRACT_LANGUAGE, exactly_one=False
                )
        except GeocoderServiceError as e:
            logger.warning(f"Geocoding with {name} failed: {e}")
            continue

        if location:
            return {
                "type": "Point",
                "coordinates": [location[0].longitude, location[0].latitude],
            }
        else:
            logger.debug(f"No location found for {search}")
            return None
    # exc_info to help sentry with grouping
    logger.error(
        f"All geocoding attempts failed. Search string was {search}", exc_info=True
    )
    return None


def _format_opencage_location(location) -> str:
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


def _format_nominatim_location(location) -> str:
    if re.match(r"^\d", location.split(",")[0]):
        # Number at the beginning: probably a house number
        return location.split(",")[1] + " " + location.split(",")[0]
    else:
        return location.split(",")[0]


def latlng_to_address(lat, lng) -> str:
    search_str = str(lat) + ", " + str(lng)

    if settings.GEOEXTRACT_ENGINE == "opencage":
        if not settings.OPENCAGE_KEY:
            raise ValueError(
                "OpenCage Data is selected as Geocoder, however no OPENCAGE_KEY is set"
            )
        location = OpenCage(settings.OPENCAGE_KEY).reverse(search_str)
        if location:
            return _format_opencage_location(location)
    else:
        location = Nominatim(
            user_agent=slugify(settings.PRODUCT_NAME) + "/1.0"
        ).reverse(search_str)
        if len(location) > 0:
            return _format_nominatim_location(location[0])
    return search_str
