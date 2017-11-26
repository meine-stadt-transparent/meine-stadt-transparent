import concurrent
import hashlib
import logging
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor as Pool
from typing import Callable, TypeVar, List

import gi
import requests
from django.db import transaction

from .oparl_objects import OParlObjects

gi.require_version('OParl', '0.2')
from gi.repository import GLib, OParl


class OParlImport(OParlObjects):
    """ Imports a oparl 1.0 compatible endpoint into the database.

    The importer can be customized by overriding this class.
    """
    T = TypeVar('T')

    def __init__(self, options):
        super().__init__(options)
        os.makedirs(self.storagefolder, exist_ok=True)
        os.makedirs(self.cachefolder, exist_ok=True)

        # Initialize the liboparl client
        self.client = OParl.Client()
        self.client.connect("resolve_url", self.resolve)
        try:
            self.system = self.client.open(self.entrypoint)
        except GLib.Error as e:
            self.logger.fatal("Failed to load entrypoint: {}".format(e))
            self.logger.fatal("Aborting.")
            return

    def resolve(self, _, url: str):
        cachepath = os.path.join(self.cachefolder, hashlib.sha1(url.encode('utf-8')).hexdigest())
        if self.use_cache and os.path.isfile(cachepath):
            logging.info("Cached: " + url)
            with open(cachepath) as file:
                data = file.read()
                return OParl.ResolveUrlResult(resolved_data=data, success=True, status_code=304)

        try:
            logging.info("Loading: " + url)
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
            logging.info("Batch finished")

    def list_caught(self, objectlistfn: Callable[[], List[T]], fn: Callable[[T], None]) -> int:
        """ Downloads and parses a body list and llogs all errors immediately.

        This is a fixup for python's broken error handling with threadpools.
        """
        err_count = 0
        objectlist = objectlistfn()
        for item in objectlist:
            try:
                fn(item)
            except Exception as e:
                logging.error("An error occured:", e, file=sys.stderr)
                logging.error(traceback.format_exc(), file=sys.stderr)
                self.errorlist.append((item.get_id(), e, traceback.format_exc()))
                err_count += 1

        return err_count

    def get_bodies(self):
        return self.system.get_body()

    def bodies_singlethread(self, bodies):
        logging.info("Creating bodies")
        for body in bodies:
            self.body(body)
        logging.info("Finished creating bodies")

    def run_singlethread(self):
        bodies = self.get_bodies()
        self.bodies_singlethread(bodies)

        logging.info("Creating objects")
        for body in bodies:
            self.list_batched(body.get_paper, self.paper)
            self.list_batched(body.get_person, self.person)
            self.list_batched(body.get_organization, self.organization)
            self.list_batched(body.get_meeting, self.meeting)

        logging.info("Finished creating objects")
        self.add_missing_associations()

    def bodies_multithread(self, bodies):
        logging.info("Creating bodies")
        # Ensure all bodies exist when calling the other methods

        with Pool(self.threadcount) as executor:
            results = executor.map(self.body, bodies)

        # Raise those exceptions
        list(results)
        logging.info("Finished creating bodies")

    def run_multithreaded(self):
        bodies = self.get_bodies()
        self.bodies_multithread(bodies)

        with Pool(self.threadcount) as executor:
            logging.info("Submitting concurrent tasks")
            futures = {}
            for body in bodies:
                future = executor.submit(self.list_caught, body.get_paper, self.paper)
                futures[future] = body.get_short_name() or body.get_name() + ": Paper"
                future = executor.submit(self.list_caught, body.get_person, self.person)
                futures[future] = body.get_short_name() or body.get_name() + ": Person"
                future = executor.submit(self.list_caught, body.get_organization, self.organization)
                futures[future] = body.get_short_name() or body.get_name() + ": Organization"
                future = executor.submit(self.list_caught, body.get_meeting, self.meeting)
                futures[future] = body.get_short_name() or body.get_name() + ": Meeting"
            logging.info("Finished submitting concurrent tasks")
            for future in concurrent.futures.as_completed(futures):
                err_count = future.result()
                if err_count == 0:
                    logging.info("Finished Successfully: ", futures[future])
                else:
                    logging.info("Finished with {} errors: {}".format(err_count, futures[future]))

        logging.info("Finished creating objects")
        self.add_missing_associations()

        for i in self.errorlist:
            logging.error(i)

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
            logging.error("There was an error in the Process for {}".format(config["entrypoint"]), file=sys.stderr)
            logging.error(traceback.format_exc(), file=sys.stderr)
            return False
        return True
