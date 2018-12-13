import concurrent
import logging
import os
import traceback
from concurrent.futures import ThreadPoolExecutor as Pool
from typing import Callable, TypeVar, List

import gi
from django.db import transaction

from mainapp.models import Body
from .oparl_objects import OParlObjects

gi.require_version("OParl", "0.4")
from gi.repository import GLib, OParl


class OParlImport(OParlObjects):
    """ Imports a oparl 1.0 compatible endpoint into the database.

    The importer can be customized by overriding this class.
    """

    T = TypeVar("T")

    def __init__(self, options, resolver):
        super().__init__(options, resolver)

        # Initialize the liboparl client
        self.client = OParl.Client()
        self.client.connect("resolve_url", lambda _, url: self.resolver.resolve(url))
        try:
            self.system = self.client.open(self.entrypoint)
        except GLib.Error as e:
            self.logger.fatal("Failed to load entrypoint: {}".format(e))
            self.logger.fatal("Aborting.")
            return

    def list_batched(
        self, objectlistfn: Callable[[], List[T]], fn: Callable[[T], None]
    ):
        """ Loads a list using liboparl and then inserts it batchwise into the database. """
        objectlist = objectlistfn()
        for i in range(0, len(objectlist), self.batchsize):
            with transaction.atomic():
                for item in objectlist[i : i + self.batchsize]:
                    fn(item)
            self.logger.info("Batch finished")

    def list_caught(
        self, objectlistfn: Callable[[], List[T]], fn: Callable[[T], None]
    ) -> int:
        """ Downloads and parses a body list and llogs all errors immediately.

        This is a fixup for python's broken error handling with threadpools.
        """
        err_count = 0
        objectlist = objectlistfn()
        for item in objectlist:
            try:
                fn(item)
            except Exception as e:
                self.logger.error("An error occured: {}".format(e))
                self.logger.error(traceback.format_exc())
                self.errorlist.append((item.get_id(), e, traceback.format_exc()))
                err_count += 1

        return err_count

    def get_bodies(self) -> List[OParl.Body]:
        return self.system.get_body()

    def bodies_singlethread(self, bodies):
        self.logger.info("Creating bodies")
        for body in bodies:
            self.body(body)
        self.logger.info("Finished creating bodies")

    def run_singlethread(self):
        bodies = self.get_bodies()
        self.bodies_singlethread(bodies)

        self.logger.info("Creating objects")
        for body in bodies:
            if not Body.objects.filter(oparl_id=body.get_id()).first():
                if body.get_deleted():
                    self.logger.error(
                        "Body {} which has been deleted on the server side, skipping.".format(
                            body.get_id()
                        )
                    )
                else:
                    self.logger.error(
                        "Body {} is not in the database even it has not been deleted on the server "
                        "side. This looks fishy".format(body.get_id)
                    )
                continue
            self.list_batched(body.get_paper, self.paper)
            self.list_batched(body.get_person, self.person)
            self.list_batched(body.get_organization, self.organization)
            self.list_batched(body.get_meeting, self.meeting)

        self.logger.info("Finished creating objects")
        self.add_missing_associations()

    def bodies_multithread(self, bodies):
        self.logger.info("Creating bodies")
        # Ensure all bodies exist when calling the other methods

        with Pool(self.threadcount) as executor:
            results = executor.map(self.body, bodies)

        # Raise those exceptions
        list(results)
        self.logger.info("Finished creating bodies")

    def run_multithreaded(self):
        bodies = self.get_bodies()
        self.bodies_multithread(bodies)

        with Pool(self.threadcount) as executor:
            self.logger.info("Submitting concurrent tasks")
            futures = {}
            for body in bodies:
                future = executor.submit(self.list_caught, body.get_paper, self.paper)
                futures[future] = body.get_short_name() or body.get_name() + ": Paper"
                future = executor.submit(self.list_caught, body.get_person, self.person)
                futures[future] = body.get_short_name() or body.get_name() + ": Person"
                future = executor.submit(
                    self.list_caught, body.get_organization, self.organization
                )
                futures[future] = (
                    body.get_short_name() or body.get_name() + ": Organization"
                )
                future = executor.submit(
                    self.list_caught, body.get_meeting, self.meeting
                )
                futures[future] = body.get_short_name() or body.get_name() + ": Meeting"
            self.logger.info("Finished submitting concurrent tasks")
            for future in concurrent.futures.as_completed(futures):
                err_count = future.result()
                if err_count == 0:
                    self.logger.info(
                        "Finished Successfully: {}".format(futures[future])
                    )
                else:
                    self.logger.info(
                        "Finished with {} errors: {}".format(err_count, futures[future])
                    )

        self.logger.info("Finished creating objects")
        self.add_missing_associations()

        for i in self.errorlist:
            self.logger.error(i)

    def run(self):
        if self.no_threads:
            self.run_singlethread()
        else:
            self.run_multithreaded()

    @classmethod
    def run_static(cls, config):
        """ This method is requried as instances of this class can't be moved to other processes """
        logger = logging.getLogger(__name__)
        try:
            runner = cls(config)
            runner.run_multithreaded()
        except Exception:
            logger.error(
                "There was an error in the Process for {}".format(config["entrypoint"])
            )
            logger.error(traceback.format_exc())
            return False
        return True
