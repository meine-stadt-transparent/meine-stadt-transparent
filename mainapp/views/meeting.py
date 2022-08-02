import json
from datetime import date
from typing import List

import dateutil.parser
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.timezone import now, get_current_timezone
from django.utils.translation import gettext as _
from icalendar import Calendar
from pytz import timezone
from slugify import slugify

from mainapp.models import Meeting, Organization, AgendaItem, Person
from mainapp.views.utils import build_map_object


def calendar(request, init_view=None, init_date=None):
    context = {
        "default_date": date.today().strftime("%Y-%m-%d"),
        "default_view": settings.CALENDAR_DEFAULT_VIEW,
        "hide_weekends": 1 if settings.CALENDAR_HIDE_WEEKENDS else 0,
        "min_time": settings.CALENDAR_MIN_TIME,
        "max_time": settings.CALENDAR_MAX_TIME,
    }

    if init_view and init_date:
        context["init_date"] = init_date
        context["init_view"] = init_view
    else:
        context["init_date"] = context["default_date"]
        context["init_view"] = context["default_view"]

    return render(request, "mainapp/calendar.html", context)


def calendar_data(request):
    """Callback for the javascript library to get the meetings."""
    # For some reason I do neither understand nor investigated fullcalendar sometimes send a date without timezone and
    # sometimes a date with 00:00:00 and timezone.
    start = dateutil.parser.parse(request.GET["start"])
    end = dateutil.parser.parse(request.GET["end"])

    # We assume that if the user chose a date he meant the date in the timezone of the data
    local_time_zone = timezone(settings.TIME_ZONE)

    if start.tzinfo is None or start.tzinfo.utcoffset(start) is None:
        start = local_time_zone.localize(start)
    if end.tzinfo is None or end.tzinfo.utcoffset(end) is None:
        end = local_time_zone.localize(end)

    meetings = Meeting.objects.filter(start__gte=start, start__lte=end)
    data = []
    for meeting in meetings:
        class_name = []
        if meeting.cancelled:
            class_name.append("cancelled")
        data.append(
            {
                "title": meeting.name,
                "start": meeting.start.isoformat()
                if meeting.start is not None
                else None,
                "end": meeting.end.isoformat() if meeting.end is not None else None,
                "details": reverse("meeting", args=[meeting.id]),
                "className": class_name,
            }
        )
    return JsonResponse(data, safe=False)


def meeting(request, pk):
    selected_meeting = get_object_or_404(Meeting, id=pk)

    if selected_meeting.location and selected_meeting.location.geometry:
        location_geom = selected_meeting.location.geometry
    else:
        location_geom = None

    agenda_items = selected_meeting.agendaitem_set.prefetch_related(
        "consultation__paper__main_file"
    ).all()

    # The persons can be listed both in the organization and in the meeting,
    # but we're only interested in the ones only in the meeting
    meeting_persons = set(
        Person.objects.filter(membership__organization__meeting=selected_meeting).all()
    )
    extra_persons = set(selected_meeting.persons.all()) - meeting_persons

    if selected_meeting.end:
        end = selected_meeting.end.replace(tzinfo=get_current_timezone())
    else:
        end = None

    context = {
        "meeting": selected_meeting,
        # Workaround missing timezone support in sqlite and mariadb
        "start": selected_meeting.start.replace(tzinfo=get_current_timezone()),
        "end": end,
        "map": build_map_object(),
        "location_json": json.dumps(location_geom),
        "agenda_items": agenda_items,
        "extra_persons": extra_persons,
    }
    # Try to find a previous or following meetings using the organization
    # Excludes meetings with more than one organization
    if selected_meeting.organizations.count() == 1:
        organization = selected_meeting.organizations.first()
        query = (
            Meeting.objects.annotate(count=Count("organizations"))
            .filter(count=1)
            .filter(organizations=organization)
            .order_by("start")
        )

        context["previous"] = query.filter(start__lt=selected_meeting.start).last()
        context["following"] = query.filter(start__gt=selected_meeting.start).first()

    if selected_meeting.location:
        for_maps = selected_meeting.location.for_maps()
        context["google_maps_url"] = "http://maps.google.de/maps?" + urlencode(
            {"q": for_maps}
        )
        context["osm_url"] = "https://www.openstreetmap.org/search?" + urlencode(
            {"query": for_maps}
        )

    return render(request, "mainapp/meeting.html", context)


def historical_meeting(request, pk):
    """WIP"""
    historical_meeting = get_object_or_404(Meeting.history, history_id=pk)

    AgendaItem.history.filter(meeting_id=historical_meeting.id).filter(
        history_date__lte=historical_meeting.history_date + relativedelta(minutes=1)
    ).count()

    context = {
        "meeting": historical_meeting.instance,
        "historical": historical_meeting,
        "seo_robots_index": "noindex",
    }
    return render(request, "mainapp/meeting.html", context)


def build_ical_response(meetings: List[Meeting], filename: str):
    cal = Calendar()
    cal.add("prodid", "-//{}//".format(settings.PRODUCT_NAME))
    cal.add("version", "2.0")

    for meeting in meetings:
        cal.add_component(meeting.as_ical_event())

    response = HttpResponse(cal.to_ical(), content_type="text/calendar")
    response["Content-Disposition"] = "inline; filename={}.ics".format(
        slugify(filename)
    )
    return response


def meeting_ical(_request, pk):
    meeting = get_object_or_404(Meeting, id=pk)

    filename = meeting.short_name or meeting.name or _("Meeting")

    return build_ical_response([meeting], filename)


def organizazion_ical(_request, pk):
    committee = get_object_or_404(Organization, id=pk)
    meetings = committee.meeting_set.prefetch_related("location").all()
    filename = committee.short_name or committee.name or _("Meeting Series")

    return build_ical_response(meetings, filename)


def calendar_ical(_request):
    """Returns an ical file containing all meetings from -6 months from now."""
    meetings = (
        Meeting.objects.filter(start__gt=now() + relativedelta(months=-6))
        .order_by("start")
        .prefetch_related("location")
        .all()
    )
    filename = _("All Meetings")
    return build_ical_response(meetings, filename)
