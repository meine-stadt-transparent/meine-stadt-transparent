from django.conf import settings
from geopy import OpenCage


def get_geolocator():
    # @TODO Support other geocoders as well
    geolocator = OpenCage(settings.OPENCAGEDATA_KEY)
    return geolocator


def geocode(search_str: str):
    geolocator = get_geolocator()
    location = geolocator.geocode(search_str, language="de", exactly_one=False)
    if len(location) == 0:
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


def latlng_to_address(lat, lng):
    geolocator = get_geolocator()
    location = geolocator.reverse(str(lat) + ", " + str(lng))
    if len(location) > 0:
        return _format_opencage_location(location[0])
    else:
        return str(lat) + ", " + str(lng)
