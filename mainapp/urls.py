from django.conf.urls import url
from django.views.generic import DetailView
from django.views.static import serve

import mainapp.views.views
from mainapp.views.profile import profile_view, profile_delete
from meine_stadt_transparent import settings
from . import views
from .models import Location, Body
from .models import LegislativeTerm


def simple_model_view(name: str, model):
    name_minus = name.replace(' ', '-')
    name_underscore = name.replace(' ', '_')
    template_name = 'mainapp/{}.html'.format(name_underscore)
    dt = DetailView.as_view(model=model, template_name=template_name, context_object_name=name_underscore)
    return url(r'^{}/(?P<pk>[0-9]+)/$'.format(name_minus), dt, name=name_minus)


urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^search/query/(?P<query>.*)/$', views.search_index, name='search'),
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
    url(r'^department/(?P<pk>[0-9]+)/$', views.department, name='department'),
    url(r'^committee/(?P<pk>[0-9]+)/$', views.committee, name='committee'),
    url(r'^parliamentary-group/(?P<pk>[0-9]+)/$', views.parliamentary_group, name='parliamentary-group'),
    url(r'^person/(?P<pk>[0-9]+)/$', views.person, name='person'),
    url(r'^meeting/(?P<pk>[0-9]+)/$', views.meeting, name='meeting'),
    url(r'^paper/(?P<pk>[0-9]+)/$', views.paper, name='paper'),
    url(r'^file/(?P<pk>[0-9]+)/$', views.file, name='file'),
    url(r'^meeting/(?P<pk>[0-9]+)/ical/$', views.meeting_ical, name='meeting-ical'),
    url(r'^committee/(?P<pk>[0-9]+)/ical/$', views.committee_ical, name='committee_ical'),
    simple_model_view('body', Body),
    simple_model_view('legislative term', LegislativeTerm),
    simple_model_view('location', Location),
    url(r'^profile/$', profile_view, name='profile-home'),
    url(r'^profile/delete/$', profile_delete, name='profile-delete'),
    # TODO: Warn in production because one should use nginx directly. Also, mime types
    url(r'^resource/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}, name="resource"),
    url(r'^404/$', views.error404, name="error-404"),
    url(r'^500/$', views.error500, name="error-500"),
]
