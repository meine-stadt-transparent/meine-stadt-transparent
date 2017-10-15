import concurrent
import hashlib
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor as Pool
from typing import Callable, TypeVar, List

import gi
import requests
from django.db import transaction

from .oparl_import_objects import OParlImportObjects

gi.require_version('OParl', '0.2')
from gi.repository import GLib, OParl


class OParlImport(OParlImportObjects):
    """ Imports a oparl 1.0 compatible endpoint into the database.

    The importer can be customized by overriding this class.
    """
    T = TypeVar('T')

    def __init__(self, options):
        super().__init__(options)
        self.client = OParl.Client()

        self.client.connect("resolve_url", self.resolve)
        os.makedirs(self.storagefolder, exist_ok=True)
        os.makedirs(self.cachefolder, exist_ok=True)

    def resolve(self, _, url: str):
        cachepath = os.path.join(self.cachefolder, hashlib.sha1(url.encode('utf-8')).hexdigest())
        if self.use_cache and os.path.isfile(cachepath):
            print("Cached: " + url)
            with open(cachepath) as file:
                data = file.read()
                return OParl.ResolveUrlResult(resolved_data=data, success=True, status_code=304)

        try:
            print("Loading: " + url)
            req = requests.get(url)
        except Exception as e:
            self.logger.error("Error loading url: ", e)
            return OParl.ResolveUrlResult(resolved_data=None, success=False, status_code=-1)

        content = req.content.decode('utf-8')

        try:
            req.raise_for_status()
        except Exception as e:
            self.logger.error("HTTP status code error: ", e)
            return OParl.ResolveUrlResult(resolved_data=content, success=False, status_code=req.status_code)

        with open(cachepath, 'w') as file:
            file.write(content)

        return OParl.ResolveUrlResult(resolved_data=content, success=True, status_code=req.status_code)

    def list_batched(self, objectlistfn: Callable[[], List[T]], fn: Callable[[T], None]):
        """ Loads a list using liboparl and then inserts it batchwise into the database. """
        objectlist = objectlistfn()
        for i in range(0, len(objectlist), self.batchsize):
            with transaction.atomic():
                for item in objectlist[i:i + self.batchsize]:
                    fn(item)
            print("Batch finished")

    @staticmethod
    def list_caught(objectlistfn: Callable[[], List[T]], fn: Callable[[T], None]):
        """ Downloads and parses a body list and prints all errors immediately.
        This is a fixup for python's broken error handling with threadpools.
        """
        try:
            objectlist = objectlistfn()
            for item in objectlist:
                fn(item)
        except Exception as e:
            print("An error occured:", e)
            traceback.print_exc()

    def run_singlethread(self):
        try:
            system = self.client.open(self.entrypoint)
        except GLib.Error as e:
            self.logger.fatal("Failed to load entrypoint: {}".format(e))
            self.logger.fatal("Aborting.")
            return
        bodies = system.get_body()

        print("Creating bodies")
        for body in bodies:
            self.body(body)
        print("Finished creating bodies")

        print("Creating objects")
        for body in bodies:
            if self.with_papers:
                self.list_batched(body.get_paper, self.paper)
            if self.with_persons:
                self.list_batched(body.get_person, self.person)
            if self.with_organizations:
                self.list_batched(body.get_organization, self.organization)
            if self.with_meetings:
                self.list_batched(body.get_meeting, self.meeting)

        print("Finished creating objects")
        self.add_missing_associations()

    def run_multithreaded(self):
        try:
            system = self.client.open(self.entrypoint)
        except GLib.Error as e:
            self.logger.fatal("Failed to load entrypoint: {}".format(e))
            self.logger.fatal("Aborting.")
            return
        bodies = system.get_body()

        print("Creating bodies")
        # Ensure all bodies exist when calling the other methods

        with Pool(self.threadcount) as executor:
            results = executor.map(self.body, bodies)

        # Raise those exceptions
        list(results)
        print("Finished creating bodies")

        with Pool(self.threadcount) as executor:
            print("Submitting concurrent tasks")
            futures = {}
            for body in bodies:
                if self.with_papers:
                    future = executor.submit(self.list_caught, body.get_paper, self.paper)
                    futures[future] = "{}: Paper".format(body.get_short_name())
                if self.with_persons:
                    future = executor.submit(self.list_caught, body.get_person, self.person)
                    futures[future] = "{}: Person".format(body.get_short_name())
                if self.with_organizations:
                    future = executor.submit(self.list_caught, body.get_organization, self.organization)
                    futures[future] = "{}: Organization".format(body.get_short_name())
                if self.with_meetings:
                    future = executor.submit(self.list_caught, body.get_meeting, self.meeting)
                    futures[future] = "{}: Meeting".format(body.get_short_name())
            print("Finished submitting concurrent tasks")
            for future in concurrent.futures.as_completed(futures):
                print("Finished", futures[future])
                future.result()

        print("Finished creating objects")
        self.add_missing_associations()

    def run(self):
        if self.no_threads:
            self.run_singlethread()
        else:
            self.run_multithreaded()

    @classmethod
    def run_static(cls, config):
        """ This method is requried as instances of this class can't be moved to other processes """
        try:
            runner = cls(config)
            runner.run_multithreaded()
        except Exception:
            print("There was an error in the Process for {}".format(config["entrypoint"]), file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            return False
        return True
