from django.contrib.auth.models import User
from django.db import models

from mainapp.functions.search import params_to_search_string, search_string_to_params
from mainapp.functions.search_notification_tools import (
    params_to_human_string,
    params_are_equal,
)


class UserAlert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    search_string = models.TextField(null=False, blank=False)
    created = models.DateTimeField(auto_now_add=True)
    last_match = models.DateTimeField(null=True)

    def get_search_params(self):
        return search_string_to_params(self.search_string)

    def set_search_params(self, params: dict):
        self.search_string = params_to_search_string(params)

    def __str__(self):
        return params_to_human_string(self.get_search_params())

    @classmethod
    def find_user_alert(cls, user, search_params):
        alerts = UserAlert.objects.filter(user=user).all()
        for alert in alerts:
            if params_are_equal(search_params, alert.get_search_params()):
                return alert
        return None

    @classmethod
    def user_has_alert(cls, user, search_params):
        found = UserAlert.find_user_alert(user, search_params)
        if found:
            return True
        else:
            return False
