import concurrent
import traceback
from concurrent.futures import ThreadPoolExecutor as Pool
from typing import Callable, TypeVar, List, Any, Dict, Generator

from mainapp.models import Body
from .oparl_objects import OParlObjects


class OParlImport(OParlObjects):
    """ Imports a oparl 1.0 compatible endpoint into the database.

    The importer can be customized by overriding this class.
    """

    T = TypeVar("T")

    def external_list_lazy(self, url: str) -> Generator[Dict[str, Any], None, None]:
        next_url = url
        while next_url:
            response = self.resolve(next_url).resolved_data
            for element in response["data"]:
                yield element
            next_url = response["links"].get("next")

    def process_list(self, list_url: str, fn: Callable[[Dict[str, Any]], Any]) -> None:
        """ This was meant for batchwise processing, but is disabled since the apis can
        be so slow that it timed out """
        for item in self.external_list_lazy(list_url):
            fn(item)

    def list_caught(
        self, objectlistfn: Callable[[], List[T]], fn: Callable[[T], Any]
    ) -> int:
        """ Downloads and parses a body list and logs all errors immediately.

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

    def get_bodies(self) -> List[Dict[str, Any]]:
        system = self.resolve(self.entrypoint).resolved_data
        return list(self.external_list_lazy(system["body"]))

    def bodies(self, bodies: List[Dict[str, Any]]):
        self.logger.info("Creating bodies")
        for body in bodies:
            self.body(body)
        self.logger.info("Finished creating bodies")

    def run_singlethread(self) -> None:
        bodies = self.get_bodies()
        self.bodies(bodies)

        self.logger.info("Creating objects")
        for body in bodies:
            if not Body.objects.filter(oparl_id=body["id"]).first():
                if body["deleted"]:
                    self.logger.error(
                        "Body {} which has been deleted on the server side, skipping.".format(
                            body["id"]
                        )
                    )
                else:
                    self.logger.error(
                        "Body {} is not in the database even it has not been deleted on the server "
                        "side. This looks fishy".format(body["id"])
                    )
                continue

            self.import_body_objects(body)

    def import_body_objects(self, body):
        self.logger.info("Importing the papers")
        for paper in self.external_list_lazy(body["paper"]):
            self.paper(paper)
        self.logger.info("Importing the persons")
        for person in self.external_list_lazy(body["person"]):
            self.person(person)
        self.logger.info("Importing the organizations")
        for organization in self.external_list_lazy(body["organization"]):
            self.organization(organization)
        self.logger.info("Importing the meetings")
        for meeting in self.external_list_lazy(body["meeting"]):
            self.meeting(meeting)
        self.logger.info("Adding the embedded objects")
        self.add_embedded_objects()
        self.logger.info("Adding some missing associations")
        self.add_missing_associations()

    def run_multithreaded(self) -> None:
        bodies = self.get_bodies()
        self.bodies(bodies)

        with Pool(self.threadcount) as executor:
            self.logger.info("Submitting concurrent tasks")
            futures = {}
            for body in bodies:
                future = executor.submit(self.list_caught, body["paper"], self.paper)
                futures[future] = body.get("shortName") or body.get("name") + ": Paper"
                future = executor.submit(self.list_caught, body["person"], self.person)
                futures[future] = body.get("shortName") or body.get("name") + ": Person"
                future = executor.submit(
                    self.list_caught, body["organization"], self.organization
                )
                futures[future] = (
                    body.get("shortName") or body.get("name") + ": Organization"
                )
                future = executor.submit(
                    self.list_caught, body["meeting"], self.meeting
                )
                futures[future] = (
                    body.get("shortName") or body.get("name") + ": Meeting"
                )
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
        self.add_embedded_objects()
        self.add_missing_associations()

        for i in self.errorlist:
            self.logger.error(i)

    def run(self) -> None:
        if self.no_threads:
            self.run_singlethread()
        else:
            self.run_multithreaded()
