from django.conf.urls import url
from django.views.generic import DetailView

from mainapp.views_profile import ProfileHomeView
from . import views
from .models import File, Location, Meeting, Body
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
    url(r'^search/suggest$', views.search_autosuggest, name='search_autosuggest'),
    url(r'^contact/$', views.info_contact, name='info_contact'),
    url(r'^about/$', views.about, name='about'),
    url(r'^persons/$', views.persons, name='persons'),
    url(r'^calendar/$', views.calendar, name='calendar'),
    url(r'^calendar/data/$', views.calendar_data, name='calendar_data'),
    url(r'^privacy/$', views.info_privacy, name='info_privacy'),
    url(r'^person/(?P<pk>[0-9]+)$', views.person, name='person'),
    url(r'^meeting/(?P<pk>[0-9]+)$', views.meeting, name='meeting'),
    url(r'^meeting/(?P<pk>[0-9]+)/ical$', views.meeting_ical, name='meeting-ical'),
    url(r'^committee/(?P<pk>[0-9]+)/ical$', views.committee_ical, name='committee_ical'),
    simple_model_view('body', Body),
    simple_model_view('committee', Committee),
    simple_model_view('department', Department),
    simple_model_view('file', File),
    simple_model_view('legislative term', LegislativeTerm),
    simple_model_view('location', Location),
    simple_model_view('paper', Paper),
    simple_model_view('parliamentary group', ParliamentaryGroup),
    url(r'^profile$', ProfileHomeView.as_view(), name='profile-home'),
    url(r'^404$', views.error404, name="error-404"),
    url(r'^500', views.error500, name="error-500"),
]

