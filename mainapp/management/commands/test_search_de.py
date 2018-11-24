"""
The whether the elasticsearch analyzer yields the right tokens for the german analyzer
"""

from django.core.management.base import BaseCommand
from elasticsearch_dsl import Index

from mainapp.documents.index import get_text_analyzer


class Command(BaseCommand):
    help = "Search for some predefined terms to check how the search is working"

    def handle(self, *args, **options):
        text_analyzer = get_text_analyzer("german")
        elastic_index = Index("mst_debug")
        elastic_index.close()
        elastic_index.analyzer(text_analyzer)
        elastic_index.save()
        elastic_index.open()
        elastic_index.flush()

        words = [
            "die",
            "hunde",
            "wi-fi",
            "Feuerwehr",
            "oktopoden",
            "Äpfel",
            "ging",
            "schwierigste",
        ]

        for word in words:
            analysis = elastic_index.analyze(analyzer="text_analyzer", text=word)
            tokens = [i["token"] for i in analysis["tokens"]]
            print(word, tokens)
