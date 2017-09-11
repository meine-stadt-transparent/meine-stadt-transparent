import json

from django.db.models import Q
from django.shortcuts import render, get_object_or_404

from mainapp.models.index.file import FileDocument
from mainapp.models.paper import Paper
from mainapp.models.person import Person


def index(request):
    return render(request, 'mainapp/index.html', {})


def search(request):
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
