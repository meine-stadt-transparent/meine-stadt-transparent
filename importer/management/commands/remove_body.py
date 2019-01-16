from django.core.management import BaseCommand

from mainapp.models import Body


class Command(BaseCommand):
    help = "Remove a body you had imported"

    def add_arguments(self, parser):
        parser.add_argument("body", help="The oparl id of the body you want to remove")

    def handle(self, *args, **options):
        Body.objects.get(oparl_id=options["oparl_id"]).delete()
