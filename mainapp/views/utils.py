from datetime import datetime

from django.contrib import messages
from django.urls import reverse

from mainapp.models import UserAlert


class NeedsLoginError(Exception):
    def __init__(self, redirect_url):
        self.redirect_url = redirect_url


class FilesGroupedByPaper:
    SORT_MODIFIED = "modified"

    def __init__(self, paper, files):
        self.paper = paper
        self.files = files

    @staticmethod
    def group_files_by_paper(files, sort=None):
        groups = {}
        for file in files:
            for paper in file.paper_set.all():
                if paper.id not in groups.keys():
                    groups[paper.id] = FilesGroupedByPaper(paper, [])
                groups[paper.id].files.append(file)
        groups_arr = list(groups.values())

        if sort == FilesGroupedByPaper.SORT_MODIFIED:
            groups_arr = sorted(groups_arr, key=lambda group: group.paper.modified, reverse=True)

        return groups_arr


def handle_subscribe_requests(request, search_params: dict, msg_subscribed, msg_unsubscribed, msg_already_subscribed):
    if 'subscribe' in request.POST:
        if request.user.is_anonymous:
            messages.error(request, 'In order to subscribe to new results, you need to log in')
            raise NeedsLoginError(reverse('account_login') + '?next=' + request.path)

        if UserAlert.user_has_alert(request.user, search_params):
            messages.info(request, msg_already_subscribed)
        else:
            alert = UserAlert()
            alert.user = request.user
            alert.set_search_params(search_params)
            alert.last_match = datetime.now()  # Prevent getting notifications about old entries
            alert.save()
            messages.success(request, msg_subscribed)

    if 'unsubscribe' in request.POST and request.user:
        if request.user.is_anonymous:
            messages.error(request, 'In order to subscribe to new results, you need to log in')
            raise NeedsLoginError(reverse('account_login') + '?next=' + request.path)

        alert = UserAlert.find_user_alert(request.user, search_params)
        if alert:
            alert.delete()
            messages.success(request, msg_unsubscribed)


def is_subscribed_to_search(user, params: dict):
    if not user.pk:
        return False
    else:
        return UserAlert.user_has_alert(user, params)
