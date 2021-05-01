import json
import os
import unittest
import urllib.parse

from django.core.management import call_command
from django.test import override_settings, TestCase, modify_settings
from django.test.utils import captured_stderr
from django_elasticsearch_dsl import Index
from django_elasticsearch_dsl.management.commands import search_index
from elasticsearch_dsl.connections import connections

from mainapp.documents.index import get_text_analyzer
from mainapp.functions.search import MainappSearch


@override_settings(ELASTICSEARCH_ENABLED=True)
@override_settings(ELASTICSEARCH_PREFIX="mst-test")
@modify_settings(INSTALLED_APPS={"append": "django_elasticsearch_dsl"})
def is_es_online(connection_alias="default"):
    """Source: https://github.com/sabricot/django-elasticsearch-dsl/pull/169"""
    with captured_stderr():
        es = connections.get_connection(connection_alias)
        return es.ping()


@override_settings(ELASTICSEARCH_ENABLED=True)
@override_settings(ELASTICSEARCH_PREFIX="mst-test")
@modify_settings(INSTALLED_APPS={"append": "django_elasticsearch_dsl"})
@unittest.skipUnless(is_es_online(), "Elasticsearch is offline")
class TestElasticsearch(TestCase):
    """Tests validating our elasticsearch config against a real elasticsearch instance.

    Since I don't want to require elasticsearch to run the tests,"""

    fixtures = ["search.json"]

    allow_database_queries = True
    maxDiff = 100000

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        call_command(search_index.Command(), action="rebuild", force=True)

    def test_scoring(self):
        """Checks that the search results are in the intended order

        1234/89: Checks that looking for reference numbers works and checks that the slash
        (which is split by the tokenizer) works
        """
        fixtures_dir = "testdata/elasticsearch_scoring"
        for filename in os.listdir(fixtures_dir):
            with open(os.path.join(fixtures_dir, filename)) as fp:
                expected = json.load(fp)
            query = urllib.parse.unquote(filename.replace(".json", ""))
            search = MainappSearch({"searchterm": query})
            actual = search.execute().to_dict()
            for i in ["took", "timed_out", "_shards", "_faceted_search"]:
                del actual[i]
            self.assertEqual(expected, actual, filename)

    def test_tokenization(self):
        """
        The whether the elasticsearch analyzer yields the right tokens for the german analyzer.

        Check the comments in mainapp.documents.index for more details
        """
        tokenizations = {
            "die": [],
            "hunde": ["hunde", "hund"],
            "wi-fi": ["wi", "fi"],
            "Feuerwehr": ["feuerwehr"],  # Would ideally split the words
            "oktopoden": ["oktopoden", "oktopod"],
            "Äpfel": ["äpfel", "apfel"],
            "ging": ["ging"],
            "schwierigste": ["schwierigste", "schwierig"],
            "1234/89": ["1234", "89"],  # Would be better if it included "1234/89"
        }

        text_analyzer = get_text_analyzer("german")
        elastic_index = Index("mst-test-tokenization")
        if not elastic_index.exists():
            elastic_index.create()
        elastic_index.close()
        elastic_index.analyzer(text_analyzer)
        elastic_index.save()
        elastic_index.open()
        elastic_index.flush()

        for word, expected_tokens in tokenizations.items():
            analysis = elastic_index.analyze(
                body={"analyzer": "text_analyzer", "text": word}
            )
            actual_tokens = [i["token"] for i in analysis["tokens"]]
            self.assertEqual(expected_tokens, actual_tokens, "Word was {}".format(word))
