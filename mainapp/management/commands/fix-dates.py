import datetime

from django.core.management.base import BaseCommand
from django.db.models import F
from pytz.reference import Local

from mainapp.models import Paper, File


class Command(BaseCommand):
    help = 'After the initial import, this command guesses the created- and modified-Attribute of papers and files'

    def add_arguments(self, parser):
        help_str = 'The date of the first import in the format YYYY-MM-DD'
        parser.add_argument('import_date', type=str, help=help_str)

        help_str = 'If no date can be determined, this will be used as fallback. Should be far in the past.'
        parser.add_argument('fallback_date', type=str, help=help_str)

    def handle(self, *args, **options):
        import_date = datetime.datetime.strptime(options['import_date'] + " 23:59:59", '%Y-%m-%d %H:%M:%S') \
            .astimezone(Local)
        fallback_date = datetime.datetime.strptime(options['fallback_date'], '%Y-%m-%d').astimezone(Local)

        print("Fixing papers...")
        num = Paper.objects.filter(created__gte=import_date, legal_date__lt=import_date) \
            .update(created=F('legal_date'), modified=F('legal_date'))
        print("=> Changed records: ", num)
        num = Paper.objects.filter(legal_date=None).update(created=fallback_date)
        print("=> Not determinable: ", num)

        print("Fixing files...")
        num = File.objects.filter(created__gte=import_date, legal_date__lt=import_date) \
            .update(created=F('legal_date'), modified=F('legal_date'))
        print("=> Changed records: ", num)
        num = File.objects.filter(legal_date=None).update(created=fallback_date)
        print("=> Not determinable: ", num)
