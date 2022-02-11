from io import BytesIO
from typing import Optional

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from mainapp.functions.minio import minio_client, minio_pgp_keys_bucket


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        null=True,
        related_name="profile",
        verbose_name=_("User"),
        on_delete=models.CASCADE,
    )
    # Normally pgp keys are 40 chars long (for sha-1), but we're going to use some padding in case a different
    # hash is used
    pgp_key_fingerprint = models.CharField(max_length=64, null=True, blank=True)

    def add_pgp_key(self, pgp_key_fingerprint: str, pgp_key: str):
        """This should eventually be abstracted away into a file manager class"""
        key_bytes = pgp_key.encode()
        minio_client().put_object(
            minio_pgp_keys_bucket,
            pgp_key_fingerprint,
            BytesIO(key_bytes),
            len(key_bytes),
        )

        self.pgp_key_fingerprint = pgp_key_fingerprint
        self.save()

    def remove_pgp_key(self):
        # If the user clicks "remove" when the key is already removed, we can ignore that
        if not self.pgp_key_fingerprint:
            return

        minio_client().remove_object(minio_pgp_keys_bucket, self.pgp_key_fingerprint)

        self.pgp_key_fingerprint = None
        self.save()

    def get_pgp_key(self) -> Optional[bytes]:
        """Returns fingerprint and key"""
        if not self.pgp_key_fingerprint:
            return None

        return (
            minio_client()
            .get_object(minio_pgp_keys_bucket, self.pgp_key_fingerprint)
            .read()
        )

    class Meta:
        verbose_name = _("User profile")
        verbose_name_plural = _("User profiles")

    def __unicode__(self):
        return "User profile: %s" % self.user.username

    # noinspection PyUnresolvedReferences
    def has_unverified_email_adresses(self):
        for email in self.user.emailaddress_set.all():
            if not email.verified:
                return True
        return False
