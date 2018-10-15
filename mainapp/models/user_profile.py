import os
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _


class UserProfile(models.Model):
    user = models.OneToOneField(User, null=True, related_name="profile", verbose_name=_(u'User'),
                                on_delete=models.CASCADE)
    # Normally pgp keys are 40 chars long (for sha-1), but we're going to use some padding in case a different
    # hash is used
    pgp_key_fingerprint = models.CharField(max_length=64, null=True, blank=True)

    def add_pgp_key(self, pgp_key_fingerprint: str, pgp_key: str):
        """ This should eventually be abstracted away into a file manager class """
        if not os.path.isdir(settings.PGP_KEY_ROOT):
            os.makedirs(settings.PGP_KEY_ROOT, exist_ok=True)

        with open(os.path.join(settings.PGP_KEY_ROOT, pgp_key_fingerprint), "w") as fp:
            fp.write(pgp_key)

        self.pgp_key_fingerprint = pgp_key_fingerprint
        self.save()

    def remove_pgp_key(self):
        # If the user clicks "remove" when the key is already removed, we can ignore that
        if not self.pgp_key_fingerprint:
            return

        os.remove(os.path.join(settings.PGP_KEY_ROOT, self.pgp_key_fingerprint))
        self.pgp_key_fingerprint = None
        self.save()

    def get_pgp_key(self) -> Optional[bytes]:
        """ Returns fingerprint and key """
        if not self.pgp_key_fingerprint:
            return None

        with open(os.path.join(settings.PGP_KEY_ROOT, self.pgp_key_fingerprint), "rb") as fp:
            return fp.read()

    class Meta:
        verbose_name = _('User profile')
        verbose_name_plural = _('User profiles')

    def __unicode__(self):
        return "User profile: %s" % self.user.username

    def has_unverified_email_adresses(self):
        for email in self.user.emailaddress_set.all():
            if not email.verified:
                return True
        return False
