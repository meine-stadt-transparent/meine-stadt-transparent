import logging
import re
import subprocess
import tempfile
from subprocess import CalledProcessError
from typing import Dict, List, Optional, Any, Iterable

import geoextract
import requests
from PyPDF2.pdf import PdfFileReader
from django.conf import settings
from django.db.models import QuerySet
from django.urls import reverse
from wand.color import Color
from wand.image import Image

from mainapp.functions.geo_functions import geocode
from mainapp.models import SearchStreet, Body, Location, Person, Paper

logger = logging.getLogger(__name__)


class AddressPipeline(geoextract.Pipeline):
    def __init__(self, locations, subs=None, stem="german"):
        if subs is None:
            if stem == "german":
                subs = [(r"str\b", "strasse")]
            else:
                subs = []
        normalizer = geoextract.BasicNormalizer(subs=subs, stem=stem)

        name_extractor = geoextract.NameExtractor()

        address_pattern = re.compile(
            r"""
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
        """,
            flags=re.UNICODE | re.VERBOSE,
        )

        pattern_extractor = geoextract.PatternExtractor([address_pattern])

        extractors = [pattern_extractor, name_extractor]

        keys_to_keep = ["name", "street", "house_number", "postcode", "city"]
        postprocessors = [(geoextract.KeyFilterPostprocessor(keys_to_keep))]

        super().__init__(
            locations,
            extractors=extractors,
            normalizer=normalizer,
            postprocessors=postprocessors,
        )


def cleanup_extracted_text(text: str) -> str:
    # Tries to merge hyphenated text back into whole words; last and first characters have to be lower case
    return re.sub(r"([a-z])-\s*\n([a-z])", r"\1\2", text)


def extract_text_from_pdf(pdf_file: str) -> str:
    try:
        return subprocess.check_output(["pdftotext", pdf_file, "-"]).decode(
            "utf-8", "ignore"
        )
    except CalledProcessError:
        logger.exception("Failed to run pdftotext on {}".format(pdf_file))
        return ""


def get_page_count_from_pdf(pdf_file: str) -> int:
    with open(pdf_file, "rb") as fp:
        return PdfFileReader(fp).getNumPages()


def perform_ocr_on_image(imgdata):
    headers = {
        "Ocp-Apim-Subscription-Key": settings.OCR_AZURE_KEY,
        "Content-Type": "application/octet-stream",
    }
    params = {"language": settings.OCR_AZURE_LANGUAGE, "detectOrientation ": "true"}
    ocr_url = settings.OCR_AZURE_API + "/vision/v1.0/ocr"
    response = requests.post(ocr_url, headers=headers, params=params, data=imgdata)
    response.raise_for_status()

    analysis = response.json()
    plain_text = ""
    for region in analysis["regions"]:
        for line in region["lines"]:
            for word in line["words"]:
                plain_text += word["text"] + " "
            plain_text += "\n"
        plain_text += "\n"

    return plain_text


def get_ocr_text_from_pdf(file):
    img = Image(blob=file, resolution=500)
    recognized_text = ""
    for single_image in img.sequence:
        with Image(single_image) as i:
            i.resolution = 100
            i.format = "png"
            i.background_color = Color("white")
            i.alpha_channel = "remove"

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


def create_geoextract_data(bodies: Optional[List[Body]] = None) -> List[Dict[str, str]]:
    street_names = []
    if bodies:
        streets = SearchStreet.objects.filter(bodies__in=bodies)
    else:
        streets = SearchStreet.objects.all()

    locations = []
    for street in streets:
        if street.displayed_name not in street_names:
            street_names.append(street.displayed_name)
            locations.append({"type": "street", "name": street.displayed_name})

    return locations


def get_search_string(location: Dict[str, str], fallback_city_name: str) -> str:
    search_str = ""
    if "street" in location:
        search_str += location["street"]
        if "house_number" in location:
            search_str += " " + location["house_number"]
        if "postcode" in location:
            search_str += ", " + location["postcode"] + " " + location["city"]
        elif "city" in location:
            search_str += ", " + location["city"]
        else:
            search_str += ", " + fallback_city_name
    elif "name" in location:
        search_str += location["name"] + ", " + fallback_city_name

    search_str += ", " + settings.GEOEXTRACT_SEARCH_COUNTRY
    return search_str


def format_location_name(location: Dict[str, str]) -> str:
    name = ""

    if "street" in location:
        name = location["street"]
        if "house_number" in location:
            name += " " + location["house_number"]
    elif "name" in location:
        name = location["name"]

    return name


def extract_found_locations(
    text: str, bodies: Optional[List[Body]] = None
) -> List[Dict[str, str]]:
    search_for = create_geoextract_data(bodies)
    pipeline = AddressPipeline(search_for)
    return pipeline.extract(text)


def extract_locations(
    text: str, fallback_city: str = settings.GEOEXTRACT_DEFAULT_CITY
) -> List[Location]:
    if not text:
        return []

    found_locations = extract_found_locations(text)

    locations = []
    for found_location in found_locations:
        if "name" in found_location and len(found_location["name"]) < 5:
            continue

        location_name = format_location_name(found_location)

        defaults = {"description": location_name, "is_official": False}

        location, created = Location.objects_with_deleted.get_or_create(
            description=location_name, defaults=defaults
        )

        if created:
            search_str = get_search_string(found_location, fallback_city)
            geodata = geocode(search_str)
            if geodata:
                location.geometry = {
                    "type": "Point",
                    "coordinates": [geodata["lng"], geodata["lat"]],
                }
                location.save()
            location.bodies.set([Body.objects.get(id=settings.SITE_DEFAULT_BODY)])

        locations.append(location)

    return locations


def index_papers_to_geodata(papers: List[Paper]) -> Dict[str, Any]:
    """
    :param papers: list of Paper
    :return: object
    """
    geodata = {}
    for paper in papers:
        for file in paper.all_files():
            for location in file.locations.all():
                if location.id not in geodata:
                    geodata[location.id] = {
                        "id": location.id,
                        "name": location.description,
                        "coordinates": location.geometry,
                        "papers": {},
                    }
                if paper.id not in geodata[location.id]["papers"]:
                    geodata[location.id]["papers"][paper.id] = {
                        "id": paper.id,
                        "name": paper.name,
                        "type": paper.paper_type.paper_type,
                        "url": reverse("paper", args=[paper.id]),
                        "files": [],
                    }
                geodata[location.id]["papers"][paper.id]["files"].append(
                    {
                        "id": file.id,
                        "name": file.name,
                        "url": reverse("file", args=[file.id]),
                    }
                )

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
