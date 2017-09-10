from mainapp.models import SearchStreet, File, Body
import geoextract
import re


def create_geoextract_data(bodies):
    """
    :type bodies: list of mainapp.models.Body
    :return: list
    """

    street_names = []
    streets = SearchStreet.objects.filter(bodies__in=bodies)

    locations = []
    for street in streets:
        if street.displayed_name not in street_names:
            street_names.append(street.displayed_name)
            locations.append({
                'type': 'street',
                'name': street.displayed_name
            })

    return locations


def extract_file_geodata(file_id):
    """
    :type file_id: int
    :return: list
    """
    file = File.objects.get(pk=file_id)
    bodies = Body.objects.get(pk=1)  # @TODO calulate the bodies from the actual file
    search_for = create_geoextract_data([bodies])

    #
    # STRING NORMALIZATION
    #

    # Strings must be normalized before searching and matching them. This includes
    # technical normalization (e.g. Unicode normalization), linguistic
    # normalization (e.g. stemming) and content normalization (e.g. synonym
    # handling).

    normalizer = geoextract.BasicNormalizer(subs=[(r'str\b', 'strasse')],
                                            stem='german')

    #
    # NAMES
    #

    # Many places can be referred to using just their name, for example specific
    # buildings (e.g. the Brandenburger Tor), streets (Hauptstraße) or other
    # points of interest. These can be extracted using the ``NameExtractor``.
    #
    # Note that extractor will automatically receive the (normalized) location
    # names from the pipeline we construct later, so there's no need to explicitly
    # pass them to the constructor.

    name_extractor = geoextract.NameExtractor()

    #
    # PATTERNS
    #

    # For locations that are notated using a semi-structured format (addresses)
    # the ``PatternExtractor`` is a good choice. It looks for matches of regular
    # expressions.
    #
    # The patterns should have named groups, their sub-matches will be
    # returned in the extracted locations.

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

    #
    # POSTPROCESSING
    #

    # Once locations are extracted you might want to postprocess them, for example
    # to remove certain attributes that are useful for validation but are not
    # intended for publication. Or you may want to remove a certain address that's
    # printed in the footer of all the documents you're processing.
    #
    # GeoExtract allows you to do this by using one or more postprocessors. In this
    # example we will remove all but a few keys from our location dicts.

    keys_to_keep = ['name', 'street', 'house_number', 'postcode', 'city']
    key_filter_postprocessor = geoextract.KeyFilterPostprocessor(keys_to_keep)

    #
    # PIPELINE CONSTRUCTION
    #

    # A pipeline connects all the different components.
    #
    # Here we're using custom extractors and a custom normalizer. We could also
    # provide our own code for splitting a document into chunks and for validation,
    # but for simplicity we'll use the default implementations in these cases.

    pipeline = geoextract.Pipeline(
        search_for,
        extractors=[pattern_extractor, name_extractor],
        normalizer=normalizer,
        postprocessors=[key_filter_postprocessor],
    )

    found_locations = pipeline.extract(file.parsed_text)
    return found_locations
