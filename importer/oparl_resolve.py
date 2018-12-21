import logging
from io import BytesIO

import gi
import requests
from minio.error import NoSuchKey

from mainapp.functions.minio import minio_client, minio_cache_bucket

gi.require_version("OParl", "0.4")
from gi.repository import OParl


class OParlResolver:
    """ Resolver for liboparl """

    def __init__(self, entrypoint, use_cache):
        self.entrypoint = entrypoint
        self.use_cache = use_cache
        self.logger = logging.getLogger(__name__)

    def resolve(self, url: str):
        if self.use_cache:
            try:
                data = minio_client.get_object(minio_cache_bucket, url + "-disambiguate-file")
                data = data.read().decode()
                self.logger.info("Cached: " + url)
                return OParl.ResolveUrlResult(
                    resolved_data=data, success=True, status_code=304
                )
            except NoSuchKey:
                pass

        try:
            self.logger.info("Loading: " + url)
            req = requests.get(url)
        except Exception as e:
            self.logger.error("Error loading url: ", e)
            return OParl.ResolveUrlResult(
                resolved_data=None, success=False, status_code=-1
            )

        content = req.content
        decoded = content.decode()

        try:
            req.raise_for_status()
        except Exception as e:
            self.logger.error("HTTP status code error: ", e)
            return OParl.ResolveUrlResult(
                resolved_data=decoded, success=False, status_code=req.status_code
            )

        # We need to avoid filenames where a prefix already is a file, which fails with a weird minio error
        minio_client.put_object(minio_cache_bucket, url + "-disambiguate-file", BytesIO(content), len(content))

        return OParl.ResolveUrlResult(
            resolved_data=decoded, success=True, status_code=req.status_code
        )
