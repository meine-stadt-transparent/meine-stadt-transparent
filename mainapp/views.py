import json
from datetime import date, timedelta, datetime

from django.conf import settings
from django.contrib import messages
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.translation import ugettext as _
from elasticsearch_dsl import Search
from icalendar import Calendar
# noinspection PyPackageRequirements
from slugify import slugify

from mainapp.documents import DOCUMENT_TYPES
from mainapp.functions.search_tools import params_to_query, search_string_to_params
from mainapp.models import Body, Committee, UserAlert
from mainapp.models.meeting import Meeting
from mainapp.models.paper import Paper
from mainapp.models.person import Person


def index(request):
    main_body = Body.objects.get(id=settings.SITE_DEFAULT_BODY)
    if main_body.outline:
        outline = main_body.outline.geometry
    else:
        outline = None

    document_end_date = date.today() + timedelta(days=1)
    document_start_date = document_end_date - timedelta(days=settings.SITE_INDEX_DOCUMENT_DAY)
    latest_paper = Paper \
                       .objects \
                       .filter(modified__range=[document_start_date, document_end_date]) \
                       .order_by("-modified", "-legal_date")[:10]
    for paper in latest_paper:
        setattr(paper, "type", "paper")  # The mixed results view needs this
    geo_papers = Paper \
                     .objects \
                     .filter(modified__range=[document_start_date, document_end_date]) \
                     .prefetch_related('files') \
                     .prefetch_related('files__locations')[:50]

    context = {
        'map': json.dumps({
            'center': settings.SITE_GEO_CENTER,
            'zoom': settings.SITE_GEO_INIT_ZOOM,
            'limit': settings.SITE_GEO_LIMITS,
            'outline': outline,
            'documents': _index_papers_to_geodata(geo_papers)
        }),
        'latest_paper': latest_paper,
    }
    return render(request, 'mainapp/index.html', context)


def _index_papers_to_geodata(papers):
    """
    :param papers: list of Paper
    :return: object
    """
    geodata = {}
    for paper in papers:
        for file in paper.files.all():
            for location in file.locations.all():
                if location.id not in geodata:
                    geodata[location.id] = {
                        "id": location.id,
                        "name": location.name,
                        "coordinates": location.geometry,
                        "papers": {}
                    }
                if paper.id not in geodata[location.id]['papers']:
                    geodata[location.id]['papers'][paper.id] = {
                        "id": paper.id,
                        "name": paper.name,
                        "url": reverse('paper', args=[file.id]),
                        "files": []
                    }
                geodata[location.id]['papers'][paper.id]["files"].append({
                    "id": file.id,
                    "name": file.name,
                    "url": reverse('file', args=[file.id])
                })

    return geodata


def info_privacy(request):
    return render(request, 'mainapp/info_privacy.html', {})


def info_contact(request):
    return render(request, 'mainapp/info_contact.html', {})


def about(request):
    return render(request, 'mainapp/about.html', {})


def search(request):
    if request.GET == {}:
        context = {
            "results": [],
            "options": [],
        }

        return render(request, 'mainapp/search.html', context)

    params = request.GET
    searchdict = search_string_to_params(params.get("query", ""))
    options, s = params_to_query(searchdict)

    results = []
    for hit in s.execute():
        result = hit.__dict__['_d_']  # Extract the raw fields from the hit
        result["type"] = hit.meta.doc_type.replace("_document", "").replace("_", "-")

        if hasattr(hit.meta, "highlight"):
            result["highlight"] = hit.meta.highlight.parsed_text
        results.append(result)

    context = {
        "results": results,
        "options": options,
        "document_types": DOCUMENT_TYPES,
    }

    return render(request, 'mainapp/search.html', context)


def search_autosuggest(request, query):
    if not settings.USE_ELASTICSEARCH:
        results = [{'name': _('search disabled'), 'url': reverse('index')}]
        return HttpResponse(json.dumps(results), content_type='application/json')

    response = Search(index='ris_files').query("match", autocomplete=query).execute()

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
        elif hit.meta.doc_type == 'paper_document':
            name = hit.name
            results.append({'name': name, 'url': reverse('paper', args=[hit.id])})
        else:
            print("Unknown type: %s" % hit.meta.doc_type)

    return JsonResponse(results, safe=False)


def persons(request):
    pk = settings.SITE_DEFAULT_COMMITTEE
    committee = get_object_or_404(Committee, id=pk)

    memberships = committee.committeemembership_set.all()
    parliamentarygroups = []
    members = []
    for membership in memberships:
        pers = membership.person
        groups_ids = []
        groups_css_classes = []
        groups_names = []

        for parlmember in pers.parliamentarygroupmembership_set.all():
            group = parlmember.parliamentary_group
            groups_ids.append(str(group.id))
            groups_css_classes.append("parliamentary-group-%i" % group.id)
            groups_names.append(group.name)
            if group not in parliamentarygroups:
                parliamentarygroups.append(group)

        members.append({
            'id': pers.id,
            'name': pers.name,
            'start': membership.start,
            'end': membership.end,
            'role': membership.role,
            'groups_ids': ','.join(groups_ids),
            'groups_css_classes': ' '.join(groups_css_classes),
            'groups_names': ', '.join(groups_names),
        })

    context = {
        "current_committee": committee,
        "members": members,
        "parliamentary_groups": parliamentarygroups,
    }
    return render(request, 'mainapp/persons.html', context)


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


def person(request, pk):
    selected_person = get_object_or_404(Person, id=pk)
    search_params = {"person": pk}

    if 'subscribe' in request.POST:
        if request.user:
            if UserAlert.user_has_alert(request.user, search_params):
                messages.info(request, _('You have already subscribed to this person.'))
            else:
                alert = UserAlert()
                alert.user = request.user
                alert.set_search_params(search_params)
                alert.last_match = datetime.now()  # Prevent getting notifications about old entries
                alert.save()
                messages.success(request, _('You will now receive notifications about new documents.'))
        else:
            # @TODO: Redirect to login form
            messages.error(request, 'You need to log in first')

    if 'unsubscribe' in request.POST and request.user:
        alert = UserAlert.find_user_alert(request.user, search_params)
        if alert:
            alert.delete()
            messages.success(request, _('You will no longer receive notifications.'))

    # That will become a shiny little query with just 7 joins
    filter_self = Paper.objects.filter(submitter_persons__id=pk)
    filter_committee = Paper.objects.filter(submitter_committees__committeemembership__person__id=pk)
    filer_group = Paper.objects.filter(submitter_parliamentary_groups__parliamentarygroupmembership__id=pk)
    paper = (filter_self | filter_committee | filer_group).distinct()

    if not request.user.pk:
        is_subscribed = False
    else:
        is_subscribed = UserAlert.user_has_alert(request.user, search_params)

    context = {
        "person": selected_person,
        "papers": paper,
        "is_subscribed": is_subscribed,
    }
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
        query = Meeting.objects \
            .annotate(count=Count("committees")) \
            .filter(count=1) \
            .filter(committees__id=committee.id) \
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


def error404(request):
    return render(request, "error/404.html", status=404)


def error500(request):
    return render(request, "error/500.html", status=500)
