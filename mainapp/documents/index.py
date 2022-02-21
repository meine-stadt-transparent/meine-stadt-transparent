"""
The elasticsearch index configuration

We do two kinds of queries: The fast suggest query for the suggestions in the dropdown below the
search field and the full-blown search query with filters and aggregations.

For the suggest query, we're using only autocomplete filed with the edge_ngram filter, which
generates all prefixes for a word.

For the search query we want all the text fields. For the fields with natural language (not names,
but parsed pdf texts) we want to include both the word itself (e.g. "containing") as well as
the normalized from "contain" as tokens. This way we can search for "contain", "containing" and a
misspelled "containsng" and find that word. Therefore we use "keyword_repeat" to duplicate each
word, of which then only one copy is normalized, and then use unique_stem to remove possible
adjacent duplicates.

In Elasticsearch 6.4, there is the multiplexer filter, which allows us to do that more elegantly,
and maybe even to combine it with edge_ngram, so we should switch to that after the upgrade.

I tried to do word splitting and hunspell stemming for German, but the former didn't work and
the latter didn't show any improvement with the words I tried. Maybe we'd just need a better
dictionary, but it's difficult enough to find any dicitionary and installing the custom
dictionary is also not trivial.
"""

from django.conf import settings
from elasticsearch_dsl import analyzer, token_filter

# noinspection PyProtectedMember
from elasticsearch_dsl.analysis import Analyzer


def get_autocomplete_analyzer():
    autocomplete_filter = token_filter(
        "autocomplete_filter", "edge_ngram", min_gram=1, max_gram=20
    )

    # Using this analyzer with an empty field fails, so we're using methods instead that add a space
    return analyzer(
        "autocomplete", tokenizer="standard", filter=["lowercase", autocomplete_filter]
    )


def get_text_analyzer(language: str) -> Analyzer:
    # https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis-lang-analyzer.html
    # According to https://discuss.elastic.co/t/extend-built-in-analyzers/134778/7 we do have to copy and paste

    stop = token_filter("stop", "stop", stopwords="_" + language + "_")
    stemmer = token_filter("stemmer", "stemmer", language=language)
    unique_stem = token_filter("unique_stem", "unique", only_on_same_position=True)

    # This seems to be kinda patchwork in elastic itself
    if language == "german":
        # https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis-lang-analyzer.html#german-analyzer
        # We can't use german_normalization here because that breaks with our keyword_repeat/unique_stem logic
        filters = ["keyword_repeat", "lowercase", stop, stemmer, unique_stem]
    elif language == "english":
        # https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis-lang-analyzer.html#english-analyzer
        english_possessive_stemmer = token_filter(
            "english_possessive_stemmer", "stemmer", language="possessive_english"
        )

        filters = [
            "keyword_repeat",
            english_possessive_stemmer,
            "lowercase",
            stop,
            stemmer,
            unique_stem,
        ]
    else:
        filters = ["keyword_repeat", "lowercase", stop, stemmer, unique_stem]

    return analyzer("text_analyzer", tokenizer="standard", filter=filters)


autocomplete_analyzer = get_autocomplete_analyzer()
text_analyzer = get_text_analyzer(settings.ELASTICSEARCH_LANG)
