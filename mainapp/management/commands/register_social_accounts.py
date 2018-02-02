# This is based on https://gist.github.com/getup8/7862fd86f8e48781587490f25417d7b9

from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Updates the allauth SocialApps registered in the database based on the ' \
           'SOCIALACCOUNT_PROVIDERS setting'

    def handle(self, *args, **options):
        for provider, config in settings.SOCIALACCOUNT_PROVIDERS.items():
            _, created = SocialApp.objects.update_or_create(provider=provider, defaults={
                "name": config.get('name', provider),
                "client_id": config['CLIENT_ID'],
                "secret": config['SECRET_KEY'],
                "sites": [settings.SITE_ID]
            })

            if created:
                message = 'Created social app: {}'
            else:
                message = 'Updated social app: {}'
            self.stdout.write(self.style.SUCCESS(message.format(provider)))
