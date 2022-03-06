import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django_elasticsearch_dsl.registries import registry

from django_q.tasks import schedule

from mainapp.functions.minio import setup_minio

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Set all database up (mariadb, elasticsearch and minio). "
        "This command is idempotent, i.e. you can run it how often you want"
    )

    def handle(self, *args, **options):
        self.stdout.write("# Running migrations")
        call_command("migrate")
        # https://docs.djangoproject.com/en/4.0/topics/cache/#creating-the-cache-table
        self.stdout.write("# Creating cache table")
        call_command("createcachetable")

        self.stdout.write("# Site settings")
        site = Site.objects.get_current()
        site.name = settings.SITE_NAME
        site.domain = settings.REAL_HOST
        site.save()
        Site.objects.clear_cache()

        if settings.ELASTICSEARCH_ENABLED:
            self.stdout.write("# Creating elasticsearch indices")
            # The logic comes from django_elasticsearch_dsl.managment.commands.search_index:_create
            for index in registry.get_indices(registry.get_models()):
                # noinspection PyProtectedMember
                self.stdout.write(
                    f"Creating elasticsearch index '{index._name}' if not exists"
                )
                # https://elasticsearch-py.readthedocs.io/en/master/api.html:
                # "ignore 400 cause by IndexAlreadyExistsException when creating an index"
                # See also https://github.com/elastic/elasticsearch/issues/19862
                index.create(ignore=400)
        else:
            self.stdout.write("# Elasticsearch is disabled; Not creating any indices")

        if settings.SCHEDULES_ENABLED:
            self.stdout.write("# Creating django-q schedules")

            # run `manage.py cron` every hour
            schedule("django.core.management.call_command", "cron", schedule_type="H")

        # This is more brittle, so we run it last
        self.stdout.write("# Creating minio buckets")
        setup_minio()
        logger.info("Setup successful")
