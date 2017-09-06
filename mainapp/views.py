from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader


def index(request):
    template = loader.get_template('mainapp/index.html')
    context = {}
    return HttpResponse(template.render(context, request))
