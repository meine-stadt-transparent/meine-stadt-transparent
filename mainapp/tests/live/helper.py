from elasticsearch_dsl import AttrList, AttrDict
from elasticsearch_dsl.response import Hit, AggResponse

from mainapp.functions.search import MainappSearch

hit_template = {
    "_index": "mst-test-file",
    "_type": "_doc",
    "_id": "159",
    "_source": {"id": 159},
    "highlight": {
        "name": ["long name <mark>hightlight</mark>"],
        "short_name": ["short name <mark>highlight</mark>"],
    },
}

response_premade = {
    "hits": {"total": {"relation": "eq", "value": 117}, "hits": [hit_template]},
    "aggregations": {
        "_filter_document_type": {
            "doc_count": 1337,
            "document_type": {
                "buckets": [
                    {"key": "organization_document", "doc_count": 42},
                    {"key": "person_document", "doc_count": 42},
                ]
            },
        },
        "_filter_person": {
            "doc_count": 1337,
            "person": {
                "buckets": [{"key": 1, "doc_count": 42}, {"key": 1, "doc_count": 42}]
            },
        },
        "_filter_organization": {
            "doc_count": 1337,
            "organization": {
                "buckets": [{"key": 41, "doc_count": 42}, {"key": 42, "doc_count": 42}]
            },
        },
    },
}

template = {
    "fields": {
        "id": 1,
        "name": "Title nolight",
        "type": "file",
        "type_translated": "File",
        "created": "2017-11-24T09:06:05.159381+00:00",
        "modified": "2017-12-01T10:56:37.297771+00:00",
    },
    "_score": 1,
    "doc_type": "_doc",
    "index": "mst-test-file",
    "highlight": {"name": ["Title <mark>Highlight</mark>"]},
}


class MockMainappSearch(MainappSearch):
    """The execute method is injected in the test methods"""

    def execute(self):
        hits = AttrList([Hit(template.copy())])
        hits.__setattr__("total", {"value": 1, "relation": "eq"})
        return AttrDict({"hits": hits, "facets": get_aggregations()})


def mock_search_autocomplete(*args):
    return AttrDict({"hits": []})


class MockMainappSearchEndlessScroll(MainappSearch):
    """The execute method is injected in the test for the endless scroll"""

    def execute(self):
        out = []
        for position in range(
            self._s.to_dict()["from"],
            self._s.to_dict()["from"] + self._s.to_dict()["size"],
        ):
            result = template.copy()
            result["highlight"] = {"name": ["<mark>" + str(position) + "</mark>"]}
            result["fields"] = {
                "id": position,
                "name": str(position),
                "name_escaped": str(position),
                "type": "file",
                "type_translated": "File",
                "created": "2017-11-24T09:06:05.159381+00:00",
                "modified": "2017-12-01T10:56:37.297771+00:00",
            }
            out.append(Hit(result))
        hits = AttrList(out)
        hits.__setattr__("total", {"value": len(out) * 2, "relation": "eq"})

        return AttrDict({"hits": hits, "facets": get_aggregations()})


def get_aggregations():
    # Fakes aggregation results that are sufficient for testing
    aggs = {
        "document_type": [
            ("file", 42, False),
            ("meeting", 42, False),
            ("person", 42, False),
        ],
        "person": [],
        "organization": [],
    }

    for i in range(10):
        aggs["person"].append((i, 42, False))
        aggs["organization"].append((i, 42, False))

    return AggResponse({}, {}, aggs)
