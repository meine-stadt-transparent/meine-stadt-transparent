from csp.decorators import csp_update
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.translation import gettext as _

from mainapp.models import UserProfile
from mainapp.models.user_alert import UserAlert


@login_required
@csp_update(CONNECT_SRC=("'self'", settings.SKS_KEYSERVER))
def profile_view(request):
    user = request.user
    profile = UserProfile.objects.get_or_create(user=user)[0]  # type: UserProfile

    if "removenotification" in request.POST:
        alerts = UserAlert.objects.filter(
            user_id=user.id, id=request.POST["removenotification"]
        ).all()
        if len(alerts) > 0:
            for alert in alerts:
                alert.delete()
            messages.success(
                request,
                _("You will now receive notifications about new search results."),
            )

    if settings.ENABLE_PGP and "pgp_key" in request.POST:
        pgp_key = request.POST["pgp_key"]
        if len(pgp_key) > 10000:
            raise ValueError("The pgp is too long")
        pgp_key_fingerprint = request.POST["pgp_key_fingerprint"]
        profile.add_pgp_key(pgp_key_fingerprint, pgp_key)

        messages.success(request, _("You're notifications will now be pgp encrypted"))

    if "delete_pgp_key" in request.POST:
        profile.remove_pgp_key()
        messages.success(
            request, _("You're notifications won't be pgp encrypted anymore")
        )

    context = {
        "alerts": UserAlert.objects.filter(user_id=user.id).all(),
        "profile": profile,
    }
    return render(request, "account/home.html", context)


@login_required
def profile_delete(request):
    user = request.user
    if "do_delete" in request.POST:
        for email in user.emailaddress_set.all():
            email.delete()
        if hasattr(user, "profile"):
            user.profile.delete()
        user.delete()
        return render(request, "account/delete_done.html")
    else:
        return render(request, "account/delete.html", {user: user})
