import logging

from django.conf import settings
from django.core.management import BaseCommand
from django.utils import translation

from importer.functions import import_update
from mainapp.functions.notify_users import NotifyUsers

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "To be called by an hourly cron job. Updates the oparl dataset and sends notifications to users.\n"
        "If you want more control call the import_update and notify_users individually."
    )

    def handle(self, *args, **options):
        import_update()

        translation.activate(settings.LANGUAGE_CODE)

        notifier = NotifyUsers()
        notifier.notify_all()
