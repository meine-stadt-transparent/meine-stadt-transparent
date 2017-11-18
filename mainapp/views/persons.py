import json

from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext as _

from mainapp.models import Organization, Person, Paper
from mainapp.views.utils import handle_subscribe_requests, is_subscribed_to_search


def persons(request):
    """ Shows all members of the default organization, which are made filterable by the parliamentary group
    memberships """
    pk = settings.SITE_DEFAULT_ORGANIZATION
    organizations = get_object_or_404(Organization, id=pk)

    parliamentarygroups = []
    members = []
    memberships = organizations.organizationmembership_set.all()
    for membership in memberships:
        pers = membership.person
        groups_ids = []
        groups_css_classes = []
        groups_names = []

        id = settings.PARLIAMENTARY_GROUPS_TYPE[0]
        for parlmember in pers.organizationmembership_set.filter(organization__organization_type_id=id):
            organization = parlmember.organization
            groups_ids.append(str(organization.id))
            groups_css_classes.append("organization-%i" % organization.id)
            groups_names.append(organization.name)
            if organization not in parliamentarygroups:
                parliamentarygroups.append(organization)

        members.append({
            'id': pers.id,
            'name': pers.name,
            'start': membership.start,
            'end': membership.end,
            'role': membership.role,
            'groups_ids': ','.join(groups_ids),
            'groups_classes': json.dumps(groups_css_classes),
            'groups_names': ', '.join(groups_names),
        })

    context = {
        "current_committee": organizations,
        "members": members,
        "parliamentary_groups": parliamentarygroups,
    }
    return render(request, 'mainapp/persons.html', context)


def person(request, pk):
    selected_person = get_object_or_404(Person, id=pk)
    search_params = {"person": pk}

    handle_subscribe_requests(request, search_params,
                              _('You will now receive notifications about new documents.'),
                              _('You will no longer receive notifications.'),
                              _('You have already subscribed to this person.'))

    # That will become a shiny little query with just 7 joins
    filter_self = Paper.objects.filter(submitter_persons__id=pk)
    filter_committee = Paper.objects.filter(submitter_committees__committeemembership__person__id=pk)
    filer_group = Paper.objects.filter(submitter_parliamentary_groups__organizationmembership__id=pk)
    paper = (filter_self | filter_committee | filer_group).distinct()

    context = {
        "person": selected_person,
        "papers": paper,
        "subscribable": True,
        "is_subscribed": is_subscribed_to_search(request.user, search_params),
    }
    return render(request, 'mainapp/person.html', context)
