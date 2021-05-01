from typing import Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from mainapp.models import UserProfile


# noinspection PyUnresolvedReferences
def encrypt(message: str, key: bytes) -> str:
    import pgpy
    from pgpy import PGPMessage
    from pgpy.constants import CompressionAlgorithm

    message = PGPMessage.new(message, compression=CompressionAlgorithm.Uncompressed)
    pub_key, _ = pgpy.PGPKey.from_blob(key)
    return str(pub_key.encrypt(message))


def send_mail(
    to: str,
    subject: str,
    message_text: str,
    message_html: str,
    profile: Optional[UserProfile] = None,
) -> None:
    """Sends a possibly encrypted email"""
    key = None
    if settings.ENABLE_PGP:
        if profile:
            key = profile.get_pgp_key()

        if key:
            message_text = encrypt(message_text, key)

    mail_from = settings.EMAIL_FROM_NAME + " <" + settings.EMAIL_FROM + ">"
    msg = EmailMultiAlternatives(
        subject=subject,
        body=message_text,
        from_email=mail_from,
        to=[to],
        headers={"Precedence": "bulk"},
    )

    # text/html and pgp doesn't mix well, but neither does application/gpg-encrypted and mailjet
    if not key:
        msg.attach_alternative(message_html, "text/html")
    msg.send()
