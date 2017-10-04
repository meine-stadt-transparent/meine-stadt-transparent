# -*- coding: utf-8 -*-

from braces.views import LoginRequiredMixin
from django.views.generic import TemplateView

from mainapp.models import UserProfile


class ProfileHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'mainapp/userprofiles/home.html'
    user_check_failure_path = '/comptes/signup/'

    def check_user(self, user):
        if user.is_active:
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super(ProfileHomeView, self).get_context_data(**kwargs)
        profile = UserProfile.objects.get_or_create(user=self.request.user)[0]
        context['profile'] = profile
        return context

