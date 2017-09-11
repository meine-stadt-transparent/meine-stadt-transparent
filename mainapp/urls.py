from django.conf.urls import url
from django.views.generic import DetailView

from . import views
from .models import Paper, Person, ParliamentaryGroup, Committee, Department, LegislativeTerm
from .models import Location, Meeting, MeetingSeries


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
    simple_model_view('committee', Committee),
    simple_model_view('department', Department),
    simple_model_view('legislative_term', LegislativeTerm),
    simple_model_view('location', Location),
    simple_model_view('meeting', Meeting),
    simple_model_view('meeting_series', MeetingSeries),
    simple_model_view('paper', Paper),
    simple_model_view('parliamentary group', ParliamentaryGroup),
]
