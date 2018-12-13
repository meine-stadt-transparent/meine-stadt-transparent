from collections import defaultdict
from io import BytesIO
from typing import Dict, DefaultDict

test_media_root = "testdata/media"


class MinioMock:
    storage = None  # type: DefaultDict[str, Dict[str, bytes]]

    def __init__(self):
        self.storage = defaultdict(dict)

    def put_object(self, bucket, object_name, data, _len):
        self.storage[bucket][object_name] = data.read()

    def get_object(self, bucket, object_name):
        return BytesIO(self.storage[bucket][object_name])

    def remove_object(self, bucket, object_name):
        del self.storage[bucket][object_name]
