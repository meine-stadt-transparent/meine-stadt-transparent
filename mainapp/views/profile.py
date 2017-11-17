# -*- coding: utf-8 -*-

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.translation import ugettext as _

from mainapp.models import UserProfile
from mainapp.models.user_alert import UserAlert


@login_required
def profile_view(request):
    user = request.user

    if 'removenotification' in request.POST:
        alerts = UserAlert.objects.filter(user_id=user.id, id=request.POST['removenotification']).all()
        if len(alerts) > 0:
            for alert in alerts:
                alert.delete()
            messages.success(request, _('You will now receive notifications about new search results.'))

    context = {
        'alerts': UserAlert.objects.filter(user_id=user.id).all(),
        'profile': UserProfile.objects.get_or_create(user=user)[0]
    }
    return render(request, "account/home.html", context)


@login_required
def profile_delete(request):
    user = request.user
    if 'do_delete' in request.POST:
        for email in user.emailaddress_set.all():
            email.delete()
        if hasattr(user, 'profile'):
            user.profile.delete()
        user.delete()
        return render(request, "account/delete_done.html")
    else:
        return render(request, "account/delete.html", {user: user})
