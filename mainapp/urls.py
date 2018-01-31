from django.conf.urls import url
from django.views.static import serve

import mainapp.views.views
from mainapp.views.profile import profile_view, profile_delete
from meine_stadt_transparent import settings
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^search/query/(?P<query>.*)/$', views.search_index, name='search'),
    url(r'^search/suggest/(?P<query>.*)/$', views.search_autosuggest, name='search_autosuggest'),
    url(r'^search/format_geo/(?P<lat>[\d.]+),(?P<lng>[\d.]+)/$', views.search_format_geo, name='search_format_geo'),
    url(r'^search/results_only/(?P<query>.*)/$', views.search_results_only, name='search_results_only'),
    url(r'^info/contact/$', views.info_contact, name='info_contact'),
    url(r'^info/about/$', views.info_about, name='info_about'),
    url(r'^info/privacy/$', views.info_privacy, name='info_privacy'),
    url(r'^info/feedback/$', views.info_feedback, name='info_feedback'),
    url(r'^info/learn/$', views.info_learn, name='info_learn'),
    url(r'^persons/$', views.persons, name='persons'),
    url(r'^organizations/$', mainapp.views.views.organizations, name='organizations'),
    url(r'^calendar/$', views.calendar, name='calendar'),
    url(r'^calendar/data/$', views.calendar_data, name='calendar_data'),
    url(r'^calendar/(?P<init_view>\w+)/(?P<init_date>[\d\-]+)/$', views.calendar, name='calendar_specific'),
    url(r'^organization/(?P<pk>[0-9]+)/$', views.organization, name='organization'),
    url(r'^person/(?P<pk>[0-9]+)/$', views.person, name='person'),
    url(r'^meeting/(?P<pk>[0-9]+)/$', views.meeting, name='meeting'),
    url(r'^paper/(?P<pk>[0-9]+)/$', views.paper, name='paper'),
    url(r'^paper/historical/(?P<pk>[0-9]+)/$', views.historical_paper, name='historical_paper'),
    url(r'^file/(?P<pk>[0-9]+)/$', views.file, name='file'),
    url(r'^meeting/(?P<pk>[0-9]+)/ical/$', views.meeting_ical, name='meeting-ical'),
    url(r'^organization/(?P<pk>[0-9]+)/ical/$', views.committee_ical, name='committee_ical'),
    url(r'^body/(?P<pk>[0-9]+)/$', views.body, name='body'),
    url(r'^legislative-term/(?P<pk>[0-9]+)/$', views.legislative_term, name='legislative-term'),
    url(r'^location/(?P<pk>[0-9]+)/$', views.location, name='location'),
    url(r'^profile/$', profile_view, name='profile-home'),
    url(r'^profile/delete/$', profile_delete, name='profile-delete'),
    # TODO: Warn in production because one should use nginx directly. Also, mime types
    url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}, name="media"),
    url(r'^404/$', views.error404, name="error-404"),
    url(r'^500/$', views.error500, name="error-500"),
]
