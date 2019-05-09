from django.core.management.base import BaseCommand
from elasticsearch_dsl import Index

from mainapp.documents.index import get_text_analyzer


class Command(BaseCommand):
    help = "View the tokenizations of some word with the elasticsearch tokenizer"

    def add_arguments(self, parser):
        parser.add_argument("words", nargs="+")

    def handle(self, *args, **options):
        text_analyzer = get_text_analyzer("german")
        elastic_index = Index("mst_debug")
        if not elastic_index.exists():
            elastic_index.create()
        elastic_index.close()
        elastic_index.analyzer(text_analyzer)
        elastic_index.save()
        elastic_index.open()
        elastic_index.flush()

        for word in options["words"]:
            analysis = elastic_index.analyze(
                body={"analyzer": "text_analyzer", "text": word}
            )
            tokens = [i["token"] for i in analysis["tokens"]]
            self.stdout.write("{} {}\n".format(word, tokens))
