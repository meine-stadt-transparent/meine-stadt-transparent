import logging
import sys
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from tempfile import NamedTemporaryFile
from typing import Optional, List, Type, Tuple
from typing import TypeVar, Any, Set
from urllib.parse import parse_qs, urlparse

from django import db
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError, transaction, DatabaseError
from django.template.defaultfilters import filesizeformat
from django.utils import timezone
from django.utils.translation import gettext as _
from elasticsearch import ElasticsearchException
from requests import RequestException
from tqdm import tqdm

from importer import JSON
from importer.functions import externalize
from importer.json_to_db import JsonToDb
from importer.loader import BaseLoader
from importer.models import CachedObject, ExternalList
from mainapp.functions.document_parsing import (
    extract_from_file,
    extract_locations,
    extract_persons,
    AddressPipeline,
    create_geoextract_data,
    limit_memory,
)
from mainapp.functions.minio import minio_client, minio_file_bucket
from mainapp.models import (
    LegislativeTerm,
    Location,
    Person,
    Organization,
    Membership,
    Meeting,
    Paper,
    Consultation,
    AgendaItem,
    Body,
    DefaultFields,
    File,
)

logger = logging.getLogger(__name__)


class Importer:
    lists = ["paper", "person", "meeting", "organization"]

    def __init__(
        self,
        loader: BaseLoader,
        default_body: Optional[Body] = None,
        ignore_modified: bool = False,
        download_files: bool = True,
        force_singlethread: bool = False,
    ):
        self.force_singlethread = force_singlethread
        self.ignore_modified = ignore_modified
        self.download_files = download_files

        self.loader = loader
        default_body = (
            default_body or Body.objects.filter(id=settings.SITE_DEFAULT_BODY).first()
        )
        self.converter = JsonToDb(loader, default_body=default_body)

    def run(self, body_id: str) -> None:
        [body_data] = self.load_bodies(body_id)
        self.fetch_lists_initial([body_data.data])
        [body] = self.import_bodies()
        self.converter.default_body = body
        self.import_objects()

    def import_anything(self, oparl_id: str) -> DefaultFields:
        return self.converter.import_anything(oparl_id)

    def fetch_lists_initial(self, bodies: List[JSON]) -> None:
        all_lists = []
        for body_entry in bodies:
            for list_type in self.lists:
                all_lists.append(body_entry[list_type])

        if not self.force_singlethread:
            # These lists are implemented so extremely slow that this brings a leap in performance
            with ThreadPoolExecutor() as executor:
                list(executor.map(self.fetch_list_initial, all_lists))
        else:
            for external_list in all_lists:
                self.fetch_list_initial(external_list)
        logger.info(f"Loading {all_lists} lists was successful")

    T = TypeVar("T", bound=DefaultFields)

    def import_type(
        self, type_class: Type[T], update: bool = False
    ) -> List[T]:  # noqa F821
        """Import all object of a given type"""

        type_name = type_class.__name__
        import_function = self.converter.type_to_function(type_class)
        related_function = self.converter.type_to_related_function(type_class)

        # So couldn't we make this like much faster by using bulk_create and deferring the related_function
        # after that? Well we could if we were using postgres, because with mysql django doesn't set the
        # id after saving with bulk save, which means we can't use related_function unless doing
        # really ugly hacks

        all_to_import = CachedObject.objects.filter(
            to_import=True, oparl_type=type_name
        ).all()

        logger.info(
            "Importing all {} {} (update={})".format(
                all_to_import.count(), type_name, update
            )
        )

        pbar = None
        if sys.stdout.isatty() and not settings.TESTING:
            pbar = tqdm(total=all_to_import.count())

        all_instances = []
        for to_import in all_to_import:
            if update:
                instance = (
                    type_class.objects_with_deleted.filter(
                        oparl_id=to_import.url
                    ).first()
                    or type_class()
                )
            else:
                instance = type_class()
            self.converter.init_base(
                to_import.data, instance, name_fixup=_("[Unknown]")
            )
            if not instance.deleted:
                import_function(to_import.data, instance)
                self.converter.utils.call_custom_hook(
                    "sanitize_" + type_name.lower(), instance
                )

            try:
                instance.save()
            except IntegrityError as e:
                if not e.args[1].startswith("Duplicate entry "):
                    raise
                else:
                    logger.warning(
                        f"Cyclic import with {type_name} {to_import.url} {e.args[0]}, ignoring"
                    )
            if related_function and not instance.deleted:
                related_function(to_import.data, instance)
            all_instances.append(instance)

            if pbar:
                pbar.update()

        if pbar:
            pbar.close()

        all_to_import.update(to_import=False)

        return all_instances

    def import_bodies(self, update: bool = False) -> List[Body]:
        self.import_type(LegislativeTerm, update)
        self.import_type(Location, update)
        return self.import_type(Body, update)

    def import_objects(self, update: bool = False) -> None:
        import_plan = [
            File,
            Person,
            Organization,
            Membership,
            Meeting,
            Paper,
            Consultation,
            AgendaItem,
        ]

        for type_class in import_plan:
            self.import_type(type_class, update)
        logger.info("Object import was successful")

    def load_bodies(self, single_body_id: Optional[str] = None) -> List[CachedObject]:
        self.fetch_list_initial(self.loader.system["body"])
        if single_body_id:
            bodies = [CachedObject.objects.get(url=single_body_id)]
            CachedObject.objects.filter(to_import=True, oparl_type="Body").exclude(
                url=single_body_id
            ).update(to_import=False)
        else:
            bodies = list(
                CachedObject.objects.filter(to_import=True, oparl_type="Body").all()
            )
        return bodies

    def fetch_list_initial(self, url: str) -> None:
        """Saves a complete external list as flattened json to the database"""
        logger.info(f"Fetching List {url}")

        timestamp = timezone.now()
        next_url = url
        all_objects = set()
        while next_url:
            logger.info(f"Fetching {next_url}")
            response = self.loader.load(next_url)

            objects = set()

            for element in response["data"]:
                externalized = externalize(element)
                for i in externalized:
                    if not i.data.get("deleted") and i not in all_objects:
                        objects.update(externalized)

            next_url = response["links"].get("next")

            # We can't have the that block outside the loop due to mysql's max_allowed_packet, manifesting
            # "MySQL server has gone away" https://stackoverflow.com/a/36637118/3549270
            # We'll be able to solve this a lot better after the django 2.2 update with ignore_conflicts
            try:
                # Also avoid "MySQL server has gone away" errors due to timeouts
                # https://stackoverflow.com/a/32720475/3549270
                db.close_old_connections()
                # The test are run with sqlite, which failed here with a TransactionManagementError:
                # "An error occurred in the current transaction.
                # You can't execute queries until the end of the 'atomic' block."
                # That's why we build our own atomic block
                if settings.TESTING:
                    with transaction.atomic():
                        saved_objects = CachedObject.objects.bulk_create(objects)
                else:
                    saved_objects = CachedObject.objects.bulk_create(objects)
            except IntegrityError:
                saved_objects = set()
                for i in objects:
                    defaults = {
                        "data": i.data,
                        "to_import": True,
                        "oparl_type": i.oparl_type,
                    }
                    saved_objects.add(
                        CachedObject.objects.update_or_create(
                            url=i.url, defaults=defaults
                        )[0]
                    )

            all_objects.update(saved_objects)
        logger.info(f"Found {len(all_objects)} objects in {url}")
        ExternalList(url=url, last_update=timestamp).save()

    def fetch_list_update(self, url: str) -> List[str]:
        """Saves a complete external list as flattened json to the database"""
        fetch_later = []

        timestamp = timezone.now()
        external_list = ExternalList.objects.get(url=url)
        logger.info(
            "Last modified for {}: {}".format(
                url, external_list.last_update.isoformat()
            )
        )
        # There must not be microseconds in the query datetimes
        # (Wuppertal rejects that and it's not standard compliant)
        modified_since_query = {
            "modified_since": external_list.last_update.replace(
                microsecond=0
            ).isoformat()
        }
        next_url = url
        while next_url:
            # Handles both the case where modified_since is given with
            # the next url and where it isn't
            if "modified_since" in parse_qs(urlparse(next_url).query):
                response = self.loader.load(next_url)
            else:
                response = self.loader.load(next_url, modified_since_query)
            for element in response["data"]:
                fetch_later += self._process_element(element)

            next_url = response["links"].get("next")

        external_list.last_update = timestamp
        external_list.save()

        return fetch_later

    def is_url(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False

        try:
            URLValidator()(value)
            return True
        except ValidationError:
            return False

    def _process_element(self, element: JSON) -> List[str]:
        keys_of_interest = set()  # type: Set[str]
        new = list(externalize(element, keys_of_interest))
        # Find the ids of removed embedded objects
        # This way is not elegant, but it gets the job done.
        old_element = CachedObject.objects.filter(url=element["id"]).first()
        old_urls = set()
        if old_element:
            for key in keys_of_interest:
                if isinstance(old_element.data.get(key), list):
                    old_urls.update(old_element.data[key])
                elif isinstance(old_element.data.get(key), str):
                    old_urls.add(old_element.data[key])

        removed = old_urls - {i.url for i in new}
        fetch_later = CachedObject.objects.filter(url__in=removed).values_list(
            "url", flat=True
        )
        for instance in new:
            existing = CachedObject.objects.filter(url=instance.url).first()
            if existing:
                if existing.data == instance.data:
                    continue
                else:
                    existing.data = instance.data
                    existing.to_import = True
                    existing.save()
            else:
                instance.save()
        return fetch_later

    def update(self, body_id: str) -> None:
        fetch_later = self.fetch_list_update(self.loader.system["body"])

        # We only want to import a single body, so we mark the others as already imported
        CachedObject.objects.filter(to_import=True, oparl_type="Body").exclude(
            url=body_id
        ).update(to_import=False)

        self.import_bodies(update=True)

        bodies = CachedObject.objects.filter(url=body_id).all()
        for body_entry in bodies:
            for list_type in self.lists:
                fetch_later += self.fetch_list_update(body_entry.data[list_type])

        logger.info(f"Importing {len(fetch_later)} removed embedded objects")
        for later in fetch_later:
            # We might actually have that object freshly from somewhere else
            fresh = CachedObject.objects.filter(url=later, to_import=True).exists()

            if not fresh:
                data = self.loader.load(later)
                CachedObject.objects.filter(url=later).update(
                    data=data, oparl_type=data["type"].split("/")[-1], to_import=True
                )

        self.import_objects(update=True)

    def download_and_analyze_file(
        self, file_id: int, address_pipeline: AddressPipeline, fallback_city: str
    ) -> bool:
        """
        Downloads and analyses a single file, i.e. extracting text, locations and persons.

        Returns False for http errors on downloading and True otherwise.
        """
        file = File.objects.get(id=file_id)
        url = file.get_oparl_url()

        with NamedTemporaryFile() as tmp_file:
            try:
                content, content_type = self.loader.load_file(url)
                if content_type and file.mime_type and content_type != file.mime_type:
                    logger.warning(
                        "Diverging mime types: Expected {}, got {}".format(
                            file.mime_type, content_type
                        )
                    )
                if content_type and content_type.split(";")[0] == "text/html":
                    logger.error(
                        f"File {file.id}: Content type was {content_type}, this seems to be a silent error"
                    )
                    return False
                file.mime_type = content_type or file.mime_type
                tmp_file.write(content)
                tmp_file.file.seek(0)
                file.filesize = len(content)
            except RequestException as e:
                # Normal server error
                if e.response and 400 <= e.response.status_code < 600:
                    logger.error(
                        f"File {file.id}: Failed to download {url} with error {e.response.status_code}"
                    )
                else:
                    logger.exception(f"File {file.id}: Failed to download {url}")
                return False

            logger.debug(
                "File {}: Downloaded {} ({}, {})".format(
                    file.id, url, file.mime_type, filesizeformat(file.filesize)
                )
            )

            if not settings.PROXY_ONLY_TEMPLATE:
                minio_client().put_object(
                    minio_file_bucket,
                    str(file.id),
                    tmp_file.file,
                    file.filesize,
                    content_type=file.mime_type,
                )

            # If the api has text, keep that
            if self.download_files and not file.parsed_text:
                file.parsed_text, file.page_count = extract_from_file(
                    tmp_file.file, tmp_file.name, file.mime_type, file.id
                )

        if file.parsed_text:
            locations = extract_locations(
                file.parsed_text, pipeline=address_pipeline, fallback_city=fallback_city
            )
            file.locations.set(locations)
            persons = extract_persons(
                file.name + "\n" + (file.parsed_text or "") + "\n"
            )
            file.mentioned_persons.set(persons)
            logger.debug(
                "File {}: Found {} locations and {} persons".format(
                    file.id, len(locations), len(persons)
                )
            )
        else:
            logger.warning(f"File {file.id}: Couldn't get any text")

        try:
            db.connections.close_all()
            file.save()
        except (ElasticsearchException, DatabaseError) as e:
            logger.exception(f"File {file.id}: Failed to save: {e}")
            return False

        return True

    def load_files_multiprocessing(
        self,
        address_pipeline: AddressPipeline,
        fallback_city: str,
        files: List[int],
        max_workers: Optional[int] = None,
        pbar: Optional[tqdm] = None,
    ) -> int:
        failed = 0
        with ProcessPoolExecutor(
            max_workers=max_workers, initializer=limit_memory
        ) as executor:
            tasks = [
                (
                    file,
                    executor.submit(
                        self.download_and_analyze_file,
                        file,
                        address_pipeline,
                        fallback_city,
                    ),
                )
                for file in files
            ]
            for file, task in tasks:
                try:
                    succeeded = task.result()
                except MemoryError:
                    logger.warning(
                        f"File {file}: Import failed du to excessive memory usage "
                        f"(Limit: {settings.SUBPROCESS_MAX_RAM})"
                    )
                    succeeded = False
                if not succeeded:
                    failed += 1
                if pbar:
                    pbar.update()
        return failed

    def load_files(
        self,
        fallback_city: str,
        max_workers: Optional[int] = None,
        update: bool = False,
    ) -> Tuple[int, int]:
        """Downloads and analyses the actual file for the file entries in the database.

        Returns the number of successful and failed files"""
        # This is partially bound by waiting on external resources, but mostly very cpu intensive,
        # so we can spawn a bunch of processes to make this a lot faster.
        # We need to build a list because mysql connections and process pools don't pair well.
        files = list(
            File.objects.filter(filesize__isnull=True, oparl_access_url__isnull=False)
            .order_by("-id")
            .values_list("id", flat=True)
        )
        if not files:
            logger.info("No files to import")
            return 0, 0
        logger.info(f"Downloading and analysing {len(files)} files")
        address_pipeline = AddressPipeline(create_geoextract_data())
        pbar = None
        if sys.stdout.isatty() and not settings.TESTING:
            pbar = tqdm(total=len(files))
        failed = 0
        successful = 0

        if not self.force_singlethread:
            # We need to close the database connections, which will be automatically reopen for
            # each process
            # See https://stackoverflow.com/a/10684672/3549270
            # and https://brobin.me/blog/2017/05/mutiprocessing-in-python-django-management-commands/
            db.connections.close_all()

            failed = self.load_files_multiprocessing(
                address_pipeline, fallback_city, files, max_workers, pbar
            )

        else:
            for file in files:
                succeeded = self.download_and_analyze_file(
                    file, address_pipeline, fallback_city
                )

                if not succeeded:
                    failed += 1
                else:
                    successful += 1

                if pbar:
                    pbar.update()
        if pbar:
            pbar.close()

        if failed > 0:
            logger.error(f"{failed} files failed to download")
            # not update because these might be files that failed before
            if successful == 0 and not update:
                raise RuntimeError("All files failed to download")
        logger.info("{successful} files imported successfully")

        return successful, failed
