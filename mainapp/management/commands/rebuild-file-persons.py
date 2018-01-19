import logging

from django.core.management.base import BaseCommand

from mainapp.models import File


class Command(BaseCommand):
    help = 'Rebuilds the "mentioned persons"-table'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, help="Parse only the file with the given ID")

    def parse_file(self, file: File):
        logging.info("- Parsing: " + str(file.id) + " (" + file.name + ")")
        file.rebuild_persons()
        file.save()

    def handle(self, *args, **options):
        if options['id']:
            file = File.objects.get(id=options['id'])
            self.parse_file(file)
        else:
            files = File.objects.all()
            for file in files:
                self.parse_file(file)
