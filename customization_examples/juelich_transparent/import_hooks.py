import re

"""
Using this file, you can attach sanitize-callbacks to the importer. The following functions can be used:
- sanitize_file
- sanitize_person
- sanitize_consultation
- sanitize_meeting
- sanitize_agenda_item
- sanitize_paper
- sanitize_organization

To activate these callbacks, you need to register this file as described in the readme.
"""


def sanitize_file(file):
    """
    This hook can be used to clean up some data from the API.
    In this example, we strip the "Sitzungsvorlage (...)" from the name of the file.

    :param file: mainapp.models.file
    :return: mainapp.models.file
    """

    file.name = re.sub("Sitzungsvorlage \((?P<name>.*)\)", "\g<name>", file.name, flags=re.DOTALL)

    return file


def sanitize_person(person):
    """
    This hook can be used to clean up some data from the API.
    In this example, we strip salutations like "Herr" or "Frau" from the name.

    :param person: mainapp.models.person
    :return: mainapp.models.person
    """

    for prefix in ['Frau', 'Herr', 'Herrn']:
        person.name = re.sub(r"^" + re.escape(prefix) + " ", "", person.name)

    return person
