from datetime import date
from typing import List

import dateutil.parser
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from icalendar import Calendar
# noinspection PyPackageRequirements
from pytz import timezone
from slugify import slugify

from mainapp.models import Meeting, Organization


def calendar(request, init_view=None, init_date=None):
    context = {
        'default_date': date.today().strftime("%Y-%m-%d"),
        'default_view': settings.CALENDAR_DEFAULT_VIEW,
        'hide_weekends': 1 if settings.CALENDAR_HIDE_WEEKENDS else 0,
        'min_time': settings.CALENDAR_MIN_TIME,
        'max_time': settings.CALENDAR_MAX_TIME,
    }

    if init_view and init_date:
        context['init_date'] = init_date
        context['init_view'] = init_view
    else:
        context['init_date'] = context['default_date']
        context['init_view'] = context['default_view']

    return render(request, 'mainapp/calendar.html', context)


def calendar_data(request):
    """ Callback for the javascript library to get the meetings. """
    # For some reason I do neither understand nor investigated fullcalendar sometimes send a date without timezone and
    # sometimes a date with 00:00:00 and timezone.
    start = dateutil.parser.parse(request.GET['start'])
    end = dateutil.parser.parse(request.GET['end'])

    # We assume that if the user chose a date he meant the date in the timezone of the data
    local_time_zone = timezone(settings.TIME_ZONE)

    if start.tzinfo is None or start.tzinfo.utcoffset(start) is None:
        start = local_time_zone.localize(start)
    if end.tzinfo is None or end.tzinfo.utcoffset(end) is None:
        end = local_time_zone.localize(end)

    meetings = Meeting.objects.filter(start__gte=start, start__lte=end)
    data = []
    for meeting in meetings:
        data.append({
            'title': meeting.name,
            'start': meeting.start.isoformat() if meeting.start is not None else None,
            'end': meeting.end.isoformat() if meeting.end is not None else None,
            'details': reverse('meeting', args=[meeting.id])
        })
    return JsonResponse(data, safe=False)


def meeting(request, pk):
    selected_meeting = get_object_or_404(Meeting, id=pk)

    # Format the time frame
    if selected_meeting.start:
        begin = selected_meeting.start.strftime(settings.DATETIME_FORMAT)
    else:
        begin = None
    if selected_meeting.end:
        end = selected_meeting.end.strftime(settings.DATETIME_FORMAT)
    else:
        end = None

    if not selected_meeting.end:
        time = begin
    elif selected_meeting.start.date() == selected_meeting.end.date():
        # We don't need to repeat the date
        time = "{} - {}".format(begin, selected_meeting.end.strftime(settings.TIME_FORMAT))
    else:
        time = "{} - {}".format(begin, end)

    # Try to find a previous or following meetings using the organization
    # Excludes meetings with more than one organization
    context = {
        "meeting": selected_meeting,
        "time": time
    }
    if selected_meeting.organizations.count() == 1:
        organization = selected_meeting.organizations.first()
        query = Meeting.objects \
            .annotate(count=Count("organizations")) \
            .filter(count=1) \
            .filter(organizations=organization) \
            .order_by("start")

        context["previous"] = query.filter(start__lt=selected_meeting.start).last()
        context["following"] = query.filter(start__gt=selected_meeting.start).first()

    return render(request, 'mainapp/meeting.html', context)


def build_ical(meetings: List[Meeting], filename: str):
    cal = Calendar()
    cal.add("prodid", "-//{}//".format(settings.PRODUCT_NAME))
    cal.add('version', '2.0')

    for meeting in meetings:
        cal.add_component(meeting.as_ical_event())

    response = HttpResponse(cal.to_ical(), content_type="text/calendar")
    response['Content-Disposition'] = 'inline; filename={}.ics'.format(slugify(filename))
    return response


def meeting_ical(request, pk):
    meeting = get_object_or_404(Meeting, id=pk)

    filename = meeting.short_name or meeting.name or _("Meeting")

    return build_ical([meeting], filename)


def organizazion_ical(request, pk):
    committee = get_object_or_404(Organization, id=pk)
    meetings = committee.meeting_set.all()
    filename = committee.short_name or committee.name or _("Meeting Series")

    return build_ical(meetings, filename)


def calendar_ical(request):
    """ Returns an ical file containing all meetings +/- 3 months from now. """
    meetings = Meeting.objects \
        .filter(start__gt=now() + relativedelta(months=-3)) \
        .filter(start__lt=now() + relativedelta(months=+3)) \
        .order_by("start") \
        .all()
    filename = _("All Meetings")
    return build_ical(meetings, filename)
