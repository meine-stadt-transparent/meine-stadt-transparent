import json
import logging

from django.conf import settings
from minio import Minio
from minio.error import MinioException
from urllib3.exceptions import RequestError

"""
Minio policy: files are publicly readable, cache and pgp keys are private
"""

logger = logging.getLogger(__name__)

bucket_list = ["files", "cache"]
if settings.ENABLE_PGP:
    bucket_list.append("pgp-keys")


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


def setup_minio():
    minio = minio_client()
    for bucket in bucket_list:
        # Checking beforehand is not race-safe
        try:
            minio.make_bucket(settings.MINIO_PREFIX + bucket)
            logger.info(f"Creating minio bucket {settings.MINIO_PREFIX + bucket}")
        except MinioException:
            logger.info(f"minio bucket {settings.MINIO_PREFIX + bucket} already exists")

    files_bucket = settings.MINIO_PREFIX + "files"
    minio.set_bucket_policy(
        files_bucket, json.dumps(get_read_only_policy(files_bucket))
    )


_minio_singleton = None


def minio_client() -> Minio:
    """
    If we eagerly create a minio connection, we can only allow importing inside of functions
    because otherwise django autoloading will load minio and we don't even get to mocking for the tests.
    """
    global _minio_singleton
    if not _minio_singleton:
        _minio_singleton = Minio(
            settings.MINIO_HOST,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,
        )
        # Give a helpful error message
        try:
            _minio_singleton.bucket_exists(minio_file_bucket)
        except RequestError as e:
            raise RuntimeError(
                f"Could not reach minio at {settings.MINIO_HOST}. Please make sure that minio is working."
            ) from e
    return _minio_singleton
