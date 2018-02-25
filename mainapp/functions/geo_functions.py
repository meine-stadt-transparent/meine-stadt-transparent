import re
from urllib.request import Request

from django.conf import settings
from geopy import OpenCage, Nominatim


def get_geolocator():
    if settings.GEOEXTRACT_ENGINE.lower() == 'opencagedata':
        if not settings.OPENCAGEDATA_KEY:
            raise ValueError(
                "OpenCage Data is selected as Geocoder, however no OPENCAGEDATA_KEY is set")
        geolocator = OpenCage(settings.OPENCAGEDATA_KEY)
    else:
        geolocator = Nominatim()

        # Workaround according to https://github.com/geopy/geopy/issues/262
        requester = geolocator.urlopen

        def requester_hack(req, **kwargs):
            req = Request(url=req, headers=geolocator.headers)
            return requester(req, **kwargs)

        geolocator.urlopen = requester_hack

    return geolocator


def geocode(search_str: str):
    geolocator = get_geolocator()
    location = geolocator.geocode(search_str, language="de", exactly_one=False)
    if not location or len(location) == 0:
        return None

    return {
        'lat': location[0].latitude,
        'lng': location[0].longitude,
    }


def _format_opencage_location(location):
    components = location.raw['components']
    if 'road' in components:
        address = components['road']
        if 'house_number' in components:
            address += ' ' + components['house_number']
    elif 'pedestrian' in components:
        address = components['pedestrian']
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
        if settings.GEOEXTRACT_ENGINE.lower() == 'opencagedata':
            return _format_opencage_location(location[0])
        else:
            return _format_nominatim_location(location[0])
    else:
        return str(lat) + ", " + str(lng)
