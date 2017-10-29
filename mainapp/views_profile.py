# -*- coding: utf-8 -*-

from braces.views import LoginRequiredMixin
from django.views.generic import TemplateView

from mainapp.models import UserProfile
from mainapp.models.user_alert import UserAlert


class ProfileHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'account/home.html'
    user_check_failure_path = '/comptes/signup/'

    @staticmethod
    def check_user(user):
        if user.is_active:
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super(ProfileHomeView, self).get_context_data(**kwargs)
        profile = UserProfile.objects.get_or_create(user=self.request.user)[0]
        context['alerts'] = UserAlert.objects.filter(user_id=profile.user_id).all()
        context['profile'] = profile
        return context

