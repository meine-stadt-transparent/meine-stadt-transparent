from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Sends a test-email to the given e-mail-address'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str)

    def handle(self, *args, **options):
        email = options['email']
        message_text = "Hallo 🌍"
        message_html = "<h1>Hallo 🌍</h1><p>Schön ist's hier!</p>"
        send_mail("Hallo", message_text, "Tobias <tobias@hoessl.eu>", [email], html_message=message_html)
