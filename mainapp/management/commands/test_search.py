import time
from typing import Dict, List

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django_elasticsearch_dsl import Index

from mainapp.documents.index import autocomplete_analyzer, text_analyzer
from mainapp.functions.search import search_string_to_params, MainappSearch, parse_hit


class Command(BaseCommand):
    help = "Search for some predefined terms to check how the search is working"

    def add_arguments(self, parser):
        parser.add_argument("--rebuild", action="store_true")

    def analyze(self, text: str) -> Dict[str, List[Dict]]:
        """Shows what elasticsearch does with the tokens"""

        elastic_index_file = Index(settings.ELASTICSEARCH_PREFIX + "-file")
        elastic_index_file.analyzer(autocomplete_analyzer)
        elastic_index_file.analyzer(text_analyzer)
        return elastic_index_file.analyze(
            body={"analyzer": "text_analyzer", "text": text}
        )

    def handle(self, *args, **options):
        """
        The checks:
         * "rese" should match "research", but currently doesn't
         * "contain(|sng|ing)" should match "containing" by stemming, preserving the original and fuzzy
         * "here" matches "here's" due to language analysis
         * "Knutt" should prefer "Knutt" over "Knuth", but currently prefers frequency
         * "Schulhaus" is for big german dataset performance
        """
        if options.get("rebuild"):
            start = time.perf_counter()
            call_command(
                "search_index", action="rebuild", force=True, models=["mainapp.Person"]
            )
            end = time.perf_counter()
            self.stdout.write("Total: {}\n".format(end - start))

        words = ["containing", "here's"]

        for word in words:
            self.stdout.write(
                "{} {}\n".format(
                    word, [token["token"] for token in self.analyze(word)["tokens"]]
                )
            )

        queries = [
            "rese",
            "contain",
            "containsng",
            "containing",
            "here",
            "Knutt",
            "Schulhaus",
        ]
        for query in queries:
            params = search_string_to_params(query)
            main_search = MainappSearch(params)
            executed = main_search.execute()
            self.stdout.write(
                "# {}: {} | {}\n".format(query, len(executed.hits), executed.took)
            )
            for hit in executed.hits:
                hit = parse_hit(hit)
                highlight = (
                    str(hit.get("highlight"))
                    .replace("\n", " ")
                    .replace("\r", " ")[:100]
                )
                self.stdout.write(" - {}, {}\n".format(hit["name"][:30], highlight))
