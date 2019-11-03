import datetime

from dateutil import tz
from django.core.management.base import BaseCommand

from importer.functions import fix_sort_date


class Command(BaseCommand):
    help = "After the initial import, this command guesses the sort_date-Attribute of papers and files"

    def add_arguments(self, parser):
        help_str = (
            "The date of the first import in the format YYYY-MM-DD. "
            + "All documents/files created up to this day will have the sort_date-Attribute modified."
        )
        parser.add_argument("import_date", type=str, help=help_str)

        help_str = "If no date can be determined, this will be used as fallback. Should be far in the past."
        parser.add_argument("fallback_date", type=str, help=help_str)

    def handle(self, *args, **options):
        import_date = datetime.datetime.strptime(
            options["import_date"] + " 23:59:59", "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=tz.tzlocal())
        fallback_date = datetime.datetime.strptime(
            options["fallback_date"], "%Y-%m-%d"
        ).replace(tzinfo=tz.tzlocal())

        fix_sort_date(fallback_date, import_date)
