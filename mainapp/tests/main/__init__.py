from collections import defaultdict
from io import BytesIO
from typing import Dict, DefaultDict

test_media_root = "testdata/media"


# noinspection PyUnusedLocal
class MinioMock:
    """ Currently unused, will be revived for download tests of the importer """

    storage = None  # type: DefaultDict[str, Dict[str, bytes]]

    def __init__(self):
        self.storage = defaultdict(dict)

    def put_object(self, bucket, object_name, data, *args, **kwargs):
        self.storage[bucket][object_name] = data.read()

    def fput_object(self, bucket: str, object_name: str, filepath: str):
        with open(filepath, "rb") as fp:
            self.storage[bucket][object_name] = fp.read()

    def get_object(self, bucket, object_name):
        return BytesIO(self.storage[bucket][object_name])

    def remove_object(self, bucket, object_name):
        del self.storage[bucket][object_name]
