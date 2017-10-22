# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _


class UserProfile(models.Model):
    user = models.OneToOneField(User, null=True, related_name="profile", verbose_name=_(u'User'))
    email_is_verified = models.BooleanField(default=False, verbose_name=_(u'Email is verified'))

    class Meta:
        verbose_name = _(u'User profile')
        verbose_name_plural = _(u'User profiles')

    def __unicode__(self):
        return u"User profile: %s" % self.user.username
