from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _


class UserProfile(models.Model):
    user = models.OneToOneField(User, null=True, related_name="profile", verbose_name=_(u'User'),
                                on_delete=models.CASCADE)
    # Normally pgp keys are 40 chars long (for sha-1), but we're going to use some padding in case a different
    # hash is used
    pgp_key_fingerprint = models.CharField(max_length=64, null=True, blank=True)

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
