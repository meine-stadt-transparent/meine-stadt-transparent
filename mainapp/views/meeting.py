from datetime import date

from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from icalendar import Calendar
# noinspection PyPackageRequirements
from slugify import slugify

from mainapp.models import Meeting, Organization


def calendar(request):
    context = {
        'default_date': date.today().strftime("%Y-%m-%d"),
        'default_view': settings.CALENDAR_DEFAULT_VIEW,
    }
    return render(request, 'mainapp/calendar.html', context)


def calendar_data(request):
    start = request.GET['start']
    end = request.GET['end']
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
    begin = selected_meeting.start.strftime(settings.DATETIME_FORMAT)
    end = selected_meeting.end.strftime(settings.DATETIME_FORMAT)
    if not selected_meeting.end:
        time = begin
    elif selected_meeting.start.date() == selected_meeting.end.date():
        # We don't need to repeat the date
        time = "{} - {}".format(begin, selected_meeting.end.strftime(settings.TIME_FORMAT))
    else:
        time = "{} - {}".format(begin, end)

    # Try to find a previous or following meetings using the organization
    # Excludes meetings with more than one organization
    context = {"meeting": selected_meeting, "time": time}
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


def build_ical(events, filename):
    cal = Calendar()
    cal.add("prodid", "-//{}//".format(settings.PRODUCT_NAME))
    cal.add('version', '2.0')

    for event in events:
        cal.add_component(event)

    response = HttpResponse(cal.to_ical(), content_type="text/calendar")
    response['Content-Disposition'] = 'inline; filename={}.ics'.format(slugify(filename))
    return response


def meeting_ical(_, pk):
    meeting = get_object_or_404(Meeting, id=pk)

    filename = meeting.short_name or meeting.name or _("Meeting")

    return build_ical([meeting.as_ical_event()], filename)


def committee_ical(_, pk):
    committee = get_object_or_404(Organization, id=pk)
    events = [meeting.as_ical_event() for meeting in committee.meeting_set.all()]

    filename = committee.short_name or committee.name or _("Meeting Series")

    return build_ical(events, filename)
