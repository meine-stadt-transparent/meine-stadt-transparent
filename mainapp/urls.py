from django.conf import settings
from django.urls import path, re_path

from mainapp.views import LatestPapersFeed, SearchResultsFeed
from mainapp.views.profile import profile_view, profile_delete
from . import views

urlpatterns = [
    path(r"", views.index, name="index"),
    # We have to use re_path here because we want to match the empty string
    re_path(
        r"^search/query/(?P<query>.*)/feed/$", SearchResultsFeed(), name="search-feed"
    ),
    re_path(r"^search/query/(?P<query>.*)/$", views.search, name="search"),
    re_path(
        r"^search/suggest/(?P<query>.*)/$",
        views.search_autocomplete,
        name="search_autocomplete",
    ),
    re_path(
        r"^search/results_only/(?P<query>.*)/$",
        views.search_results_only,
        name="search_results_only",
    ),
    path(
        "search/format_geo/<int:lat>,<int:lng>/",
        views.search_format_geo,
        name="search_format_geo",
    ),
    path("info/contact/", views.info_contact, name="info_contact"),
    path("info/about/", views.info_about, name="info_about"),
    path("info/privacy/", views.info_privacy, name="info_privacy"),
    path("info/feedback/", views.info_feedback, name="info_feedback"),
    path("persons/", views.persons, name="persons"),
    path("organizations/", views.organizations, name="organizations"),
    path("calendar/", views.calendar, name="calendar"),
    path("calendar/data/", views.calendar_data, name="calendar_data"),
    path(
        "calendar/<str:init_view>/<str:init_date>/",
        views.calendar,
        name="calendar_specific",
    ),
    path("calendar/ical/", views.calendar_ical, name="calendar_ical"),
    path("organization/<int:pk>/", views.organization, name="organization"),
    path("person/<int:pk>/", views.person, name="person"),
    path("paper/<int:pk>/", views.paper, name="paper"),
    path("paper/feed/", LatestPapersFeed(), name="paper-feed"),
    path("paper/historical/<int:pk>/", views.historical_paper, name="historical_paper"),
    path("file/<int:pk>/", views.file, name="file"),
    path("meeting/<int:pk>/", views.meeting, name="meeting"),
    path(
        "meeting/<int:context_meeting_id>/file/<int:pk>/",
        views.file,
        name="meeting-file",
    ),
    path("meeting/<int:pk>/ical/", views.meeting_ical, name="meeting-ical"),
    path(
        "meeting/historical/<int:pk>/",
        views.historical_meeting,
        name="historical_meeting",
    ),
    path(
        "organization/<int:pk>/ical/", views.organizazion_ical, name="organizazion_ical"
    ),
    path("body/<int:pk>/", views.body, name="body"),
    path("legislative-term/<int:pk>/", views.legislative_term, name="legislative-term"),
    path("location/<int:pk>/", views.location, name="location"),
    path("profile/", profile_view, name="profile-home"),
    path("profile/delete/", profile_delete, name="profile-delete"),
    path("file-content/<int:id>", views.file_serve, name="file-content"),
    path("robots.txt", views.robots_txt, name="robots-txt"),
    path("sitemap.xml", views.sitemap_xml, name="sitemap-xml"),
    path("opensearch.xml", views.opensearch_xml, name="opensearch-xml"),
    path("404/", views.error404, name="error-404"),
    path("500/", views.error500, name="error-500"),
]

if settings.PROXY_ONLY_TEMPLATE:
    urlpatterns.append(
        path(
            r"file-content-proxy/<original_file_id:pk>",
            views.file_serve_proxy,
            name="file-content-proxy",
        )
    )
