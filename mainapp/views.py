from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.translation import ugettext as _
from icalendar import Calendar
from slugify import slugify

from mainapp.models.index.file import FileDocument
from mainapp.models.meeting import Meeting
from mainapp.models.meeting_series import MeetingSeries
from mainapp.models.paper import Paper
from mainapp.models.person import Person


def index(request):
    return render(request, 'mainapp/index.html', {})

def info_privacy(request):
    return render(request, 'mainapp/info_privacy.html', {})

def info_contact(request):
    return render(request, 'mainapp/info_contact.html', {})

def search(request):
    # TODO: Move me to a settings file
    context = {
        'results': [],
        'lat': "50.929961",
        'lng': "6.9537318",
        'radius': "100",
    }

    if 'action' in request.POST:
        for val in ['lat', 'lng', 'radius', 'query']:
            context[val] = request.POST[val]

        s = FileDocument.search()
        query = request.POST['query']
        lat = float(request.POST['lat'])
        lng = float(request.POST['lng'])
        radius = request.POST['radius']
        if not query == '':
            s = s.filter("match", parsed_text=query)
        if not (lat == '' or lng == '' or radius == ''):
            s = s.filter("geo_distance", distance=radius + "m", coordinates={
                "lat": lat,
                "lon": lng
            })
        s = s.highlight('parsed_text', fragment_size=50)  # @TODO Does not work yet
        for hit in s:
            for fragment in hit.meta.highlight.parsed_text:
                context['results'].append(fragment)

    return render(request, 'mainapp/search.html', context)


def person(request, pk):
    person = get_object_or_404(Person, id=pk)

    # That will become a shiny little query with just 7 joins
    filter_self = Paper.objects.filter(submitter_persons__id=pk)
    filter_committee = Paper.objects.filter(submitter_committees__committeemembership__person__id=pk)
    filer_group = Paper.objects.filter(submitter_parliamentary_groups__parliamentarygroupmembership__id=pk)
    paper = (filter_self | filter_committee | filer_group).distinct()

    context = {"person": person, "papers": paper}
    return render(request, 'mainapp/person.html', context)


def build_ical(events, filename):
    cal = Calendar()
    cal.add("prodid", "-//{}//".format(settings.PRODUCT_NAME))
    cal.add('version', '2.0')

    for event in events:
        cal.add_component(event)

    response = HttpResponse(cal.to_ical(), content_type="text/calendar")
    response['Content-Disposition'] = 'inline; filename={}.ics'.format(slugify(filename))
    return response


def meeting_ical(request, pk):
    meeting = get_object_or_404(Meeting, id=pk)

    if meeting.short_name:
        filename = meeting.short_name
    elif meeting.name:
        filename = meeting.name
    else:
        filename = _("Meeting")

    return build_ical([meeting.as_ical_event()], filename)


def meeting_series_ical(request, pk):
    series = get_object_or_404(MeetingSeries, id=pk)
    events = [meeting.as_ical_event() for meeting in series.meeting_set.all()]

    if series.short_name:
        filename = series.short_name
    elif series.name:
        filename = series.name
    else:
        filename = _("Meeting Series")

    return build_ical(events, filename)
