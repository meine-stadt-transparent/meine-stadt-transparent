import json

from django.conf import settings
from minio import Minio

"""
Minio policy: files are publicly readable, cache and pgp keys are private
"""


class LazyMinio:
    """
    If we eagerly create a minio connection, we can only allow importing inside of functions
    because otherwise django autoloading will load minio and we don't even get to mocking for the tests.

    This object will behave just like a regular minio instance
    """

    bucket_list = ["files", "cache", "pgp-keys"]

    policy_read_only = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                "Resource": ["arn:aws:s3:::meine-stadt-transparent-files"],
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": ["arn:aws:s3:::meine-stadt-transparent-files/*"],
            },
        ],
    }

    # noinspection PyMissingConstructor
    def __init__(self):
        self.minio = None

    def init_minio(self):
        self.minio = Minio(
            settings.MINIO_HOST,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,
        )

        for bucket in self.bucket_list:
            if not minio_client.bucket_exists(settings.MINIO_PREFIX + bucket):
                minio_client.make_bucket(settings.MINIO_PREFIX + bucket)

        minio_client.set_bucket_policy(
            settings.MINIO_PREFIX + "files", json.dumps(self.policy_read_only)
        )

    def __getattr__(self, item):
        if not self.minio:
            self.init_minio()

        return getattr(self.minio, item)


minio_client = LazyMinio()

minio_file_bucket = settings.MINIO_PREFIX + "files"
minio_cache_bucket = settings.MINIO_PREFIX + "cache"
minio_pgp_keys_buckets = settings.MINIO_PREFIX + "pgp-keys"
