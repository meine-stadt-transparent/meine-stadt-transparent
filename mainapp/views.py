from django.db.models import Q
from django.shortcuts import render, get_object_or_404

from mainapp.models.index.file import FileDocument
from mainapp.models.paper import Paper
from mainapp.models.person import Person


def index(request):
    return render(request, 'mainapp/index.html', {})


def search(request):
    context = {'results': []}

    if 'action' in request.POST:
        query = request.POST['query']
        s = FileDocument.search().filter("match", parsed_text=query)
        for hit in s:
            context['results'].append(hit.parsed_text)

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
