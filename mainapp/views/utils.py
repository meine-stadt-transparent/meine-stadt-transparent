import json
from typing import Optional, List, Dict, Any

from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from mainapp.models import UserAlert, Body, Paper


class NeedsLoginError(Exception):
    def __init__(self, redirect_url):
        self.redirect_url = redirect_url


def index_papers_to_geodata(papers: List[Paper]) -> Dict[str, Any]:
    """
    :param papers: list of Paper
    :return: object
    """
    geodata = {}
    for paper in papers:
        for file in paper.all_files():
            for location in file.locations.all():
                if location.id not in geodata:
                    geodata[location.id] = {
                        "id": location.id,
                        "name": location.description,
                        "coordinates": location.geometry,
                        "papers": {},
                    }
                if paper.id not in geodata[location.id]["papers"]:
                    if paper.paper_type:
                        paper_type = paper.paper_type.paper_type
                    else:
                        paper_type = _("Paper")
                    geodata[location.id]["papers"][paper.id] = {
                        "id": paper.id,
                        "name": paper.name,
                        "type": paper_type,
                        "url": reverse("paper", args=[paper.id]),
                        "files": [],
                    }
                geodata[location.id]["papers"][paper.id]["files"].append(
                    {
                        "id": file.id,
                        "name": file.name,
                        "url": reverse("file", args=[file.id]),
                    }
                )

    return geodata


def handle_subscribe_requests(
    request,
    search_params: dict,
    msg_subscribed,
    msg_unsubscribed,
    msg_already_subscribed,
):
    if "subscribe" in request.POST:
        if request.user.is_anonymous:
            messages.error(
                request, "In order to subscribe to new results, you need to log in"
            )
            raise NeedsLoginError(reverse("account_login") + "?next=" + request.path)

        if UserAlert.user_has_alert(request.user, search_params):
            messages.info(request, msg_already_subscribed)
        else:
            alert = UserAlert()
            alert.user = request.user
            alert.set_search_params(search_params)
            alert.last_match = (
                timezone.now()
            )  # Prevent getting notifications about old entries
            alert.save()
            messages.success(request, msg_subscribed)

    if "unsubscribe" in request.POST and request.user:
        if request.user.is_anonymous:
            messages.error(
                request, "In order to subscribe to new results, you need to log in"
            )
            raise NeedsLoginError(reverse("account_login") + "?next=" + request.path)

        alert = UserAlert.find_user_alert(request.user, search_params)
        if alert:
            alert.delete()
            messages.success(request, msg_unsubscribed)


def is_subscribed_to_search(user, params: dict):
    if not user.pk:
        return False
    else:
        return UserAlert.user_has_alert(user, params)


def build_map_object(body: Optional[Body] = None, geo_papers=None):
    if not body:
        body = Body.objects.get(id=settings.SITE_DEFAULT_BODY)

    if body.outline:
        outline = body.outline.geometry
    else:
        outline = None

    map_obj = {
        "outline": outline,
        "tiles": {
            "provider": settings.MAP_TILES_PROVIDER,
            "url": settings.MAP_TILES_URL,
            "token": settings.MAPBOX_TOKEN,
        },
    }

    if geo_papers:
        map_obj["documents"] = index_papers_to_geodata(geo_papers)

    return json.dumps(map_obj)
