import json
from typing import Dict, List

from django.core.management.base import BaseCommand

from mainapp.documents.index import elastic_index_file
from mainapp.functions.search_tools import search_string_to_params, MainappSearch


class Command(BaseCommand):
    help = "Executes a search query, printing the query and the raw response"

    def add_arguments(self, parser):
        parser.add_argument("--analyze", action="store_true")
        parser.add_argument("search")

    def analyze(self, text: str) -> Dict[str, List[Dict]]:
        """ Shows what elasticsearch does with the tokens """
        return elastic_index_file.analyze(
            body={"analyzer": "text_analyzer", "text": text}
        )

    def handle(self, *args, **options):
        self.stdout.write("Searching for '{}'".format(options["search"]))
        params = search_string_to_params(options["search"])
        main_search = MainappSearch(params)
        search = main_search.build_search()
        self.stdout.write(json.dumps(search.to_dict()))
        executed = main_search.execute()
        self.stdout.write(str(executed.to_dict()))
