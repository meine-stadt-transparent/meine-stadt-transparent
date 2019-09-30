import json

from django.core.management.base import BaseCommand

from mainapp.functions.search import search_string_to_params, MainappSearch


class Command(BaseCommand):
    help = "Executes a search query, printing the query and the raw response"

    def add_arguments(self, parser):
        parser.add_argument("search")

    def handle(self, *args, **options):
        self.stdout.write("Searching for '{}'".format(options["search"]))
        params = search_string_to_params(options["search"])
        main_search = MainappSearch(params)
        search = main_search.build_search()
        self.stdout.write(json.dumps(search.to_dict()))
        executed = main_search.execute()
        del executed["_faceted_search"]
        self.stdout.write(json.dumps(executed.to_dict()))
