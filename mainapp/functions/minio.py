import json

from django.conf import settings
from minio import Minio

"""
Minio policy: files are publicly readable, cache and pgp keys are private
"""

bucket_list = ["files", "cache", "pgp-keys"]


def get_read_only_policy(bucket_name: str) -> dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                "Resource": ["arn:aws:s3:::" + bucket_name],
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": ["arn:aws:s3:::" + bucket_name + "/*"],
            },
        ],
    }


minio_file_bucket = settings.MINIO_PREFIX + "files"
minio_cache_bucket = settings.MINIO_PREFIX + "cache"
minio_pgp_keys_bucket = settings.MINIO_PREFIX + "pgp-keys"


def init_minio() -> Minio:
    minio = Minio(
        settings.MINIO_HOST,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=False,
    )

    for bucket in bucket_list:
        if not minio.bucket_exists(settings.MINIO_PREFIX + bucket):
            minio.make_bucket(settings.MINIO_PREFIX + bucket)

    files_bucket = settings.MINIO_PREFIX + "files"
    minio.set_bucket_policy(
        files_bucket, json.dumps(get_read_only_policy(files_bucket))
    )

    return minio


minio_singleton = None


def minio_client() -> Minio:
    """
    If we eagerly create a minio connection, we can only allow importing inside of functions
    because otherwise django autoloading will load minio and we don't even get to mocking for the tests.
    """
    global minio_singleton
    if not minio_singleton:
        minio_singleton = init_minio()
    return minio_singleton
