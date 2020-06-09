import json
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Union

from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger(__name__)


def get_json(data: Union[str, dict]) -> dict:
    if isinstance(data, dict):
        return data
    else:
        return json.loads(Path(data).read_text())


class ElasticsearchMock:
    request_response: List[Tuple[dict, dict]]

    def __init__(self, pairs: Dict[str, str]):
        """ Takes the paths to json files with the request and response """
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
        raise RuntimeError(f"Query not found")
