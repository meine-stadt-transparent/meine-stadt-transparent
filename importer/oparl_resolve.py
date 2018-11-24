import hashlib
import logging
import os

import gi
import requests

gi.require_version("OParl", "0.4")
from gi.repository import OParl


class OParlResolver:
    """ Resolver for liboparl """

    def __init__(self, entrypoint, cachefolder, use_cache):
        self.entrypoint = entrypoint
        self.use_cache = use_cache
        entrypoint_hash = hashlib.sha1(self.entrypoint.encode("utf-8")).hexdigest()
        self.cachefolder = os.path.join(cachefolder, entrypoint_hash)
        os.makedirs(self.cachefolder, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def resolve(self, url: str):
        cachepath = os.path.join(
            self.cachefolder, hashlib.sha1(url.encode("utf-8")).hexdigest()
        )
        if self.use_cache and os.path.isfile(cachepath):
            self.logger.info("Cached: " + url)
            with open(cachepath) as file:
                data = file.read()
                return OParl.ResolveUrlResult(
                    resolved_data=data, success=True, status_code=304
                )

        try:
            self.logger.info("Loading: " + url)
            req = requests.get(url)
        except Exception as e:
            self.logger.error("Error loading url: ", e)
            return OParl.ResolveUrlResult(
                resolved_data=None, success=False, status_code=-1
            )

        content = req.content.decode("utf-8")

        try:
            req.raise_for_status()
        except Exception as e:
            self.logger.error("HTTP status code error: ", e)
            return OParl.ResolveUrlResult(
                resolved_data=content, success=False, status_code=req.status_code
            )

        with open(cachepath, "w") as file:
            file.write(content)

        return OParl.ResolveUrlResult(
            resolved_data=content, success=True, status_code=req.status_code
        )
