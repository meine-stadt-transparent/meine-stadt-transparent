# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.db import models
from jsonfield import JSONField

from mainapp.functions.search_expression import SearchExpression


class UserAlert(models.Model):
    user = models.ForeignKey(User)
    alert_json = JSONField(null=False, blank=False)
    created = models.DateTimeField(auto_now_add=True)
    last_match = models.DateTimeField(null=True)

    def alert(self):
        return SearchExpression.create_from_json(self.alert_json)

    def __str__(self):
        return self.alert().__str__()

