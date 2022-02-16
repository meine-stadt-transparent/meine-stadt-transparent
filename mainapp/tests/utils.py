import json
import logging
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from typing import List, Tuple, Dict, Union, DefaultDict

from django.core.serializers.json import DjangoJSONEncoder
from minio.error import MinioException

logger = logging.getLogger(__name__)

test_media_root = "testdata/media"


def get_json(data: Union[str, dict]) -> dict:
    if isinstance(data, dict):
        return data
    else:
        return json.loads(Path(data).read_text())


class ElasticsearchMock:
    request_response: List[Tuple[dict, dict]]

    def __init__(self, pairs: Dict[str, str]):
        """Takes the paths to json files with the request and response"""
        self.request_response = []
        for request, response in pairs.items():
            self.request_response.append((get_json(request), get_json(response)))

    def search(self, *args, **query):
        for request, response in self.request_response:
            if query == request:
                return response

        from elasticsearch_dsl.connections import get_connection

        try:
            response = get_connection().search(*args, **query)
            logger.warning("query: " + json.dumps(query, cls=DjangoJSONEncoder))
            logger.warning("response: " + json.dumps(response, cls=DjangoJSONEncoder))
        except Exception:
            logger.warning("query: " + json.dumps(query, cls=DjangoJSONEncoder))
        raise RuntimeError("Query not found")


class MinioMock:
    """Mocks a simple minio storage with a dict"""

    storage: DefaultDict[str, Dict[str, bytes]]

    def __init__(self):
        self.storage = defaultdict(dict)

    # noinspection PyUnusedLocal
    def put_object(self, bucket, object_name, data, *args, **kwargs):
        self.storage[bucket][object_name] = data.read()

    def fput_object(self, bucket: str, object_name: str, filepath: str):
        with open(filepath, "rb") as fp:
            self.storage[bucket][object_name] = fp.read()

    def get_object(self, bucket: str, object_name: str):
        if object_name in self.storage[bucket]:
            return BytesIO(self.storage[bucket][object_name])
        else:
            raise MinioException(None)

    def remove_object(self, bucket: str, object_name: str):
        del self.storage[bucket][object_name]
