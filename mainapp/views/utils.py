from datetime import datetime

from django.contrib import messages

from mainapp.models import UserAlert


def handle_subscribe_requests(request, search_params: dict, msg_subscribed, msg_unsubscribed, msg_already_subscribed):
    if 'subscribe' in request.POST:
        if request.user:
            if UserAlert.user_has_alert(request.user, search_params):
                messages.info(request, msg_already_subscribed)
            else:
                alert = UserAlert()
                alert.user = request.user
                alert.set_search_params(search_params)
                alert.last_match = datetime.now()  # Prevent getting notifications about old entries
                alert.save()
                messages.success(request, msg_subscribed)
        else:
            # @TODO: Redirect to login form
            messages.error(request, 'You need to log in first')

    if 'unsubscribe' in request.POST and request.user:
        alert = UserAlert.find_user_alert(request.user, search_params)
        if alert:
            alert.delete()
            messages.success(request, msg_unsubscribed)


def is_subscribed_to_search(user, params: dict):
    if not user.pk:
        return False
    else:
        return UserAlert.user_has_alert(user, params)
