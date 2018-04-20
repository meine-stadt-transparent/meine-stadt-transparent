import logging
import re
import tempfile

import geoextract
import requests
import textract
from PyPDF2 import PdfFileReader
from django.conf import settings
from django.urls import reverse
from wand.color import Color
from wand.image import Image

from mainapp.functions.geo_functions import geocode
from mainapp.models import SearchStreet, Body, Location, Person

logger = logging.getLogger(__name__)


class AddressPipeline(geoextract.Pipeline):
    def __init__(self, locations, subs=None, stem='german'):
        if subs is None:
            if stem == 'german':
                subs = [(r'str\b', 'strasse')]
            else:
                subs = []
        normalizer = geoextract.BasicNormalizer(subs=subs, stem=stem)

        name_extractor = geoextract.NameExtractor()

        address_pattern = re.compile(r'''
            (?P<street>[^\W\d_](?:[^\W\d_]|\s)*[^\W\d_])
            \s+
            (?P<house_number>([1-9]\d*)[\w-]*)
            (
                \s+
                (
                    (?P<postcode>\d{5})
                    \s+
                )?
                (?P<city>([^\W\d_]|-)+)
            )?
        ''', flags=re.UNICODE | re.VERBOSE)

        pattern_extractor = geoextract.PatternExtractor([address_pattern])

        extractors = [pattern_extractor, name_extractor]

        keys_to_keep = ['name', 'street', 'house_number', 'postcode', 'city']
        postprocessors = [(geoextract.KeyFilterPostprocessor(keys_to_keep))]

        super().__init__(locations,
                         extractors=extractors,
                         normalizer=normalizer,
                         postprocessors=postprocessors)


def cleanup_extracted_text(text):
    """
    :param text: str
    :return: str
    """

    # Tries to merge hyphenated text back into whole words; last and first characters have to be lower case
    return re.sub(r"([a-z])-\s*\n([a-z])", r"\1\2", text)


def extract_text_from_pdf(pdf_file):
    """
    :param pdf_file: str
    :return: str
    """
    return str(textract.process(pdf_file))


def get_page_count_from_pdf(pdf_file):
    """
    :param pdf_file: str
    :return: int
    """
    with open(pdf_file, 'rb') as fp:
        return PdfFileReader(fp).getNumPages()


def perform_ocr_on_image(imgdata):
    headers = {'Ocp-Apim-Subscription-Key': settings.OCR_AZURE_KEY, 'Content-Type': 'application/octet-stream'}
    params = {'language': settings.OCR_AZURE_LANGUAGE, 'detectOrientation ': 'true'}
    ocr_url = settings.OCR_AZURE_API + '/vision/v1.0/ocr'
    response = requests.post(ocr_url, headers=headers, params=params, data=imgdata)
    response.raise_for_status()

    analysis = response.json()
    plain_text = ''
    for region in analysis['regions']:
        for line in region['lines']:
            for word in line['words']:
                plain_text += word['text'] + " "
            plain_text += "\n"
        plain_text += "\n"

    return plain_text


def get_ocr_text_from_pdf(pdf_file):
    img = Image(filename=pdf_file, resolution=500)
    recognized_text = ""
    for single_image in img.sequence:
        with Image(single_image) as i:
            i.resolution = 100
            i.format = 'png'
            i.background_color = Color('white')
            i.alpha_channel = 'remove'

            tmpfile = tempfile.TemporaryFile()
            i.save(file=tmpfile)
            tmpfile.seek(0)
            imgdata = tmpfile.read()
            tmpfile.close()

            # Workaround: Shrink image until the size is below Azure's upload limit of 4MB
            while len(imgdata) > 4000000:
                i.resize(round(i.width * 0.75), round(i.height * 0.75))

                tmpfile = tempfile.TemporaryFile()
                i.save(file=tmpfile)
                tmpfile.seek(0)
                imgdata = tmpfile.read()
                tmpfile.close()

            recognized_text += perform_ocr_on_image(imgdata)

    return recognized_text


def create_geoextract_data(bodies=None):
    """
    :type bodies: list of mainapp.models.Body
    :return: list
    """

    street_names = []
    if bodies:
        streets = SearchStreet.objects.filter(bodies__in=bodies)
    else:
        streets = SearchStreet.objects.all()

    locations = []
    for street in streets:
        if street.displayed_name not in street_names:
            street_names.append(street.displayed_name)
            locations.append({
                'type': 'street',
                'name': street.displayed_name
            })

    for city in settings.GEOEXTRACT_KNOWN_CITIES:
        locations.append({
            'name': city,
            'type': 'city',
        })

    return locations


def get_geodata(location, fallback_city_name):
    search_str = ''
    if 'street' in location:
        search_str += location['street']
        if 'house_number' in location:
            search_str += ' ' + location['house_number']
        if 'postcode' in location:
            search_str += ', ' + location['postcode'] + ' ' + location['city']
        elif 'city' in location:
            search_str += ', ' + location['city']
        else:
            search_str += ', ' + fallback_city_name
    elif 'name' in location:
        search_str += location['name'] + ', ' + fallback_city_name

    search_str += ', ' + settings.GEO_SEARCH_COUNTRY
    return geocode(search_str)


def format_location_name(location):
    name = ""

    if 'street' in location:
        name = location['street']
        if 'house_number' in location:
            name += ' ' + location['house_number']
    elif 'name' in location:
        name = location['name']

    return name


def extract_found_locations(text, bodies=None):
    search_for = create_geoextract_data(bodies)

    pipeline = AddressPipeline(search_for)

    return pipeline.extract(text)


def detect_relevant_bodies(_):
    body = Body.objects.get(id=settings.SITE_DEFAULT_BODY)
    return [body]


def extract_locations(text, fallback_city=settings.GEOEXTRACT_DEFAULT_CITY):
    if not text:
        return []

    found_locations = extract_found_locations(text)

    locations = []
    for found_location in found_locations:
        location_name = format_location_name(found_location)

        defaults = {
            "description": location_name,
            "is_official": False
        }

        location, created = Location.objects_with_deleted.get_or_create(description=location_name, defaults=defaults)
        if created:
            geodata = get_geodata(found_location, fallback_city)
            if geodata:
                location.geometry = {
                    "type": "Point",
                    "coordinates": [geodata['lng'], geodata['lat']]
                }
                location.save()

            bodies = detect_relevant_bodies(location)
            for body in bodies:
                location.bodies.add(body)

        locations.append(location)

    return locations


def index_papers_to_geodata(papers):
    """
    :param papers: list of Paper
    :return: object
    """
    geodata = {}
    for paper in papers:
        for file in paper.files.all():
            for location in file.locations.all():
                if location.id not in geodata:
                    geodata[location.id] = {
                        "id": location.id,
                        "name": location.description,
                        "coordinates": location.geometry,
                        "papers": {}
                    }
                if paper.id not in geodata[location.id]['papers']:
                    geodata[location.id]['papers'][paper.id] = {
                        "id": paper.id,
                        "name": paper.name,
                        "type": paper.paper_type.paper_type,
                        "url": reverse('paper', args=[paper.id]),
                        "files": []
                    }
                geodata[location.id]['papers'][paper.id]["files"].append({
                    "id": file.id,
                    "name": file.name,
                    "url": reverse('file', args=[file.id])
                })

    return geodata


def extract_persons(text):
    """
    :type text: str
    :return: list of mainapp.models.Person
    """
    persons = Person.objects.all()
    found_persons = []
    text = " " + text + " "  # Workaround to find names at the very beginning or end

    def match(name_parts):
        escaped_parts = []
        for part in name_parts:
            escaped_parts.append(re.escape(part))
        matcher = r"[^\w]" + r"[\s,]+".join(escaped_parts) + r"[^\w]"
        return re.search(matcher, text, re.I | re.S | re.U | re.MULTILINE)

    for person in persons:
        match_name = match([person.name])
        match_names = match([person.given_name, person.family_name])
        match_names_reverse = match([person.family_name, person.given_name])
        if match_name or match_names or match_names_reverse:
            found_persons.append(person)

    return found_persons
