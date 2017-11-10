from django.conf.urls import url
from django.views.generic import DetailView

import mainapp.views.views
from mainapp.views_profile import ProfileHomeView
from . import views
from .models import File, Location, Body
from .models import Paper, ParliamentaryGroup, Committee, Department, LegislativeTerm


def simple_model_view(name: str, model):
    name_minus = name.replace(' ', '-')
    name_underscore = name.replace(' ', '_')
    template_name = 'mainapp/{}.html'.format(name_underscore)
    dt = DetailView.as_view(model=model, template_name=template_name, context_object_name=name_underscore)
    return url(r'^{}/(?P<pk>[0-9]+)/$'.format(name_minus), dt, name=name_minus)


urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^search/query/(?P<query>.*)/$', views.search, name='search'),
    url(r'^search/suggest/(?P<query>.*)/$', views.search_autosuggest, name='search_autosuggest'),
    url(r'^search/results_only/(?P<query>.*)/$', views.search_results_only,
        name='search_results_only'),
    url(r'^info/contact/$', views.info_contact, name='info_contact'),
    url(r'^info/about/$', views.info_about, name='info_about'),
    url(r'^info/privacy/$', views.info_privacy, name='info_privacy'),
    url(r'^persons/$', views.persons, name='persons'),
    url(r'^organizations/$', mainapp.views.views.organizations, name='organizations'),
    url(r'^calendar/$', views.calendar, name='calendar'),
    url(r'^calendar/data/$', views.calendar_data, name='calendar_data'),
    url(r'^person/(?P<pk>[0-9]+)/$', views.person, name='person'),
    url(r'^meeting/(?P<pk>[0-9]+)/$', views.meeting, name='meeting'),
    url(r'^paper/(?P<pk>[0-9]+)/$', views.paper, name='paper'),
    url(r'^meeting/(?P<pk>[0-9]+)/ical/$', views.meeting_ical, name='meeting-ical'),
    url(r'^committee/(?P<pk>[0-9]+)/ical/$', views.committee_ical, name='committee_ical'),
    simple_model_view('body', Body),
    simple_model_view('committee', Committee),
    simple_model_view('department', Department),
    simple_model_view('file', File),
    simple_model_view('legislative term', LegislativeTerm),
    simple_model_view('location', Location),
    simple_model_view('parliamentary group', ParliamentaryGroup),
    url(r'^profile/$', ProfileHomeView.as_view(), name='profile-home'),
    url(r'^404/$', views.error404, name="error-404"),
    url(r'^500/$', views.error500, name="error-500"),
]
