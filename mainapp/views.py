import json
from datetime import date

from django.conf import settings
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.translation import ugettext as _
from elasticsearch_dsl import Search
from icalendar import Calendar
# noinspection PyPackageRequirements
from slugify import slugify

from mainapp.models import Body, Committee
from mainapp.models.index.file import FileDocument
from mainapp.models.meeting import Meeting
from mainapp.models.paper import Paper
from mainapp.models.person import Person


def index(request):
    main_body = Body.objects.get(id=settings.SITE_GEO_SHAPE_BODY_ID)
    if main_body.outline:
        outline = main_body.outline.geometry
    else:
        outline = None

    latest_paper = Paper.objects.order_by("modified", "legal_date")[:20]

    context = {
        'map': json.dumps({
            'center': settings.SITE_GEO_CENTER,
            'zoom': settings.SITE_GEO_INIT_ZOOM,
            'limit': settings.SITE_GEO_LIMITS,
            'outline': outline
        }),
        'latest_paper': latest_paper,
    }
    return render(request, 'mainapp/index.html', context)


def info_privacy(request):
    return render(request, 'mainapp/info_privacy.html', {})


def info_contact(request):
    return render(request, 'mainapp/info_contact.html', {})


def about(request):
    return render(request, 'mainapp/about.html', {})


def search(request):
    context = {
        'results': [],
        'coordinates': settings.SITE_GEO_CENTER,
        'radius': "100",
    }

    if 'query' in request.GET:
        context['query'] = request.GET['query']
        s = FileDocument.search()
        s = s.filter("match", parsed_text=request.GET['query'])
        s = s.highlight('parsed_text', fragment_size=50)  # @TODO Does not work yet
        for hit in s:
            for fragment in hit.meta.highlight.parsed_text:
                context['results'].append(fragment)

    if 'action' in request.POST:
        for val in ['radius', 'query']:
            context[val] = request.POST[val]

        context['coordinates']['lat'] = request.POST['lat']
        context['coordinates']['lng'] = request.POST['lng']

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


def search_autosuggest(request):
    ret = request.GET['query']
    s = Search(index='ris_files').query("match", autocomplete=ret)
    response = s.execute()

    bodies = Body.objects.count()

    results = []
    num_persons = num_parliamentary_groups = 0
    limit_per_type = 5

    for hit in response.hits:
        if hit.meta.doc_type == 'person_document':
            if num_persons < limit_per_type:
                results.append({'name': hit.name, 'url': reverse('person', args=[hit.id])})
                num_persons += 1
        elif hit.meta.doc_type == 'parliamentary_group_document':
            if num_parliamentary_groups < limit_per_type:
                if bodies > 1:
                    name = hit.name + " (" + hit.body.name + ")"
                else:
                    name = hit.name
                results.append({'name': name, 'url': reverse('parliamentary-group', args=[hit.id])})
                num_parliamentary_groups += 1
        elif hit.meta.doc_type == 'committee_document':
            name = hit.name
            results.append({'name': name, 'url': reverse('committee', args=[hit.id])})
        else:
            print("Unknown type: %s" % hit.meta.doc_type)

    return HttpResponse(json.dumps(results), content_type='application/json')


def persons(request):
    pk = settings.SITE_DEFAULT_COMMITTEE
    committee = get_object_or_404(Committee, id=pk)
    context = {"current_committee": committee}
    return render(request, 'mainapp/persons.html', context)


def calendar(request):
    context = {
        'default_date': date.today().strftime("%Y-%m-%d")
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


def person(request, pk):
    selected_person = get_object_or_404(Person, id=pk)

    # That will become a shiny little query with just 7 joins
    filter_self = Paper.objects.filter(submitter_persons__id=pk)
    filter_committee = Paper.objects.filter(submitter_committees__committeemembership__person__id=pk)
    filer_group = Paper.objects.filter(submitter_parliamentary_groups__parliamentarygroupmembership__id=pk)
    paper = (filter_self | filter_committee | filer_group).distinct()

    context = {"person": selected_person, "papers": paper}
    return render(request, 'mainapp/person.html', context)


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

    # Try to find a previous or following meetings using the committee
    # TODO: Can we do that with meeting with two committees ?
    context = {"meeting": selected_meeting, "time": time}
    if selected_meeting.committees.all().count() == 1:
        committee = selected_meeting.committees.first()
        context["previous"] = Meeting.objects \
            .annotate(count=Count("committees")) \
            .filter(count=1) \
            .filter(start__lt=selected_meeting.start, committees__id=committee.id) \
            .order_by("start") \
            .last()
        context["following"] = Meeting.objects.annotate(count=Count("committees")) \
            .filter(count=1) \
            .filter(start__gt=selected_meeting.start, committees__id=committee.id) \
            .order_by("start") \
            .first()

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


def meeting_ical(request, pk):
    meeting = get_object_or_404(Meeting, id=pk)

    if meeting.short_name:
        filename = meeting.short_name
    elif meeting.name:
        filename = meeting.name
    else:
        filename = _("Meeting")

    return build_ical([meeting.as_ical_event()], filename)


def committee_ical(request, pk):
    committee = get_object_or_404(Committee, id=pk)
    events = [meeting.as_ical_event() for meeting in committee.meeting_set.all()]

    if committee.short_name:
        filename = committee.short_name
    elif committee.name:
        filename = committee.name
    else:
        filename = _("Meeting Series")

    return build_ical(events, filename)
