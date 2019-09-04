import datetime

from dateutil import tz
from django.core.management.base import BaseCommand
from django.db.models import F, Subquery, OuterRef, Q

from mainapp.models import Paper, File, Consultation


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

        self.stdout.write("Fixing papers...")
        num = Paper.objects.filter(
            created__lte=import_date, legal_date__isnull=False
        ).update(sort_date=F("legal_date"), modified=F("legal_date"))
        self.stdout.write(f"=> Changed papers: {num}")

        num = Paper.objects.filter(legal_date__isnull=True).update(
            sort_date=fallback_date
        )
        self.stdout.write(f"=> Not fixable due to missing legal date: {num}")

        # Use the date of the earliest consultation
        earliest_consultation = (
            Consultation.objects.filter(paper=OuterRef("pk"), meeting__isnull=False)
            .order_by("meeting__start")
            .values("meeting__start")[:1]
        )
        num = (
            Paper.objects.filter(
                Q(sort_date=fallback_date) | ~Q(sort_date=F("legal_date"))
            )
            .annotate(earliest_consultation=Subquery(earliest_consultation))
            .filter(earliest_consultation__isnull=False)
            .update(sort_date=F("earliest_consultation"))
        )
        self.stdout.write(f"=> Fix by earliest consultation: {num}")

        self.stdout.write("Fixing files...")
        num = File.objects.filter(
            created__lte=import_date, legal_date__isnull=False
        ).update(sort_date=F("legal_date"), modified=F("legal_date"))
        self.stdout.write(f"=> Changed files: {num}")
        num = File.objects.filter(legal_date__isnull=True).update(
            sort_date=fallback_date
        )
        self.stdout.write(f"=> Not determinable: {num}")
