import logging
import os
import shutil

from django.core.management.base import BaseCommand

from importer.functions import get_importer
from importer.oparl_helper import default_options
from mainapp.functions.minio import minio_client, minio_cache_bucket
from .notifyusers import Command as NotifyUsersCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "To be called daily by a cron job. Updates the oparl dataset and sends notifications to users"

    def handle(self, *args, **options):
        importer = get_importer(default_options.copy())
        # This is darn ugly but liboparl doesn't support updates yet
        minio_client.remove_bucket(minio_cache_bucket)
        minio_client.make_bucket(minio_cache_bucket)

        importer.run_singlethread()

        notification_options = {"override_since": None, "debug": False}
        NotifyUsersCommand(stdout=self.stdout, stderr=self.stderr).handle(
            **notification_options
        )
