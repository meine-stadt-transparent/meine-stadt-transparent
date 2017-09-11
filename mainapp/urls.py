from django.conf.urls import url
from django.views.generic import DetailView

from . import views
from .models import File, Location, Meeting, MeetingSeries, Body
from .models import Paper, ParliamentaryGroup, Committee, Department, LegislativeTerm


def simple_model_view(name: str, model):
    name_minus = name.replace(' ', '-')
    name_underscore = name.replace(' ', '_')
    template_name = 'mainapp/{}.html'.format(name_underscore)
    dt = DetailView.as_view(model=model, template_name=template_name, context_object_name=name_underscore)
    return url(r'^{}/(?P<pk>[0-9]+)$'.format(name_minus), dt, name=name_minus)


urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^search/$', views.search, name='search'),
    url(r'^person/(?P<pk>[0-9]+)$', views.person, name='person'),
    url(r'^meeting/(?P<pk>[0-9]+)/ical$', views.meeting_ical, name='meeting-ical'),
    url(r'^meeting-series/(?P<pk>[0-9]+)/ical$', views.meeting_series_ical, name='meeting-series-ical'),
    simple_model_view('body', Body),
    simple_model_view('committee', Committee),
    simple_model_view('department', Department),
    simple_model_view('file', File),
    simple_model_view('legislative term', LegislativeTerm),
    simple_model_view('location', Location),
    simple_model_view('meeting', Meeting),
    simple_model_view('meeting series', MeetingSeries),
    simple_model_view('paper', Paper),
    simple_model_view('parliamentary group', ParliamentaryGroup),
]
