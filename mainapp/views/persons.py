import json
from datetime import datetime

from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.translation import ugettext as _

from mainapp.models import Organization, Person, Paper, File
from mainapp.views.utils import handle_subscribe_requests, is_subscribed_to_search, NeedsLoginError, FilesGroupedByPaper


def persons(request):
    """ Shows all members of the default organization, which are made filterable by the parliamentary group
    memberships. """
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

        group_id = settings.PARLIAMENTARY_GROUPS_TYPE[0]
        for parlmember in pers.organizationmembership_set.filter(organization__organization_type_id=group_id):
            organization = parlmember.organization
            groups_ids.append(str(organization.id))
            groups_css_classes.append("organization-%i" % organization.id)
            groups_names.append(organization.name)
            if organization not in parliamentarygroups:
                parliamentarygroups.append(organization)

        members.append({
            'id': pers.id,
            'name': pers.name_without_salutation(),
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

    try:
        handle_subscribe_requests(request, search_params,
                                  _('You will now receive notifications about new documents.'),
                                  _('You will no longer receive notifications.'),
                                  _('You have already subscribed to this person.'))
    except NeedsLoginError as err:
        return redirect(err.redirect_url)

    filter_self = Paper.objects.filter(persons__id=pk)
    filter_organization = Paper.objects.filter(organizations__organizationmembership__person__id=pk)
    paper = (filter_self | filter_organization).distinct()

    mentioned_in_files = File.objects.filter(mentioned_persons__id=pk)
    mentioned = FilesGroupedByPaper.group_files_by_paper(mentioned_in_files, FilesGroupedByPaper.SORT_MODIFIED)

    memberships_active = selected_person.organizationmembership_set.filter(end__gte=datetime.now().date()).all()
    memberships_no_end = selected_person.organizationmembership_set.filter(end__isnull=True).all()
    memberships_ended = selected_person.organizationmembership_set.filter(end__lt=datetime.now().date()).all()
    memberships = []
    if len(memberships_active) > 0:
        memberships.append(memberships_active)
    if len(memberships_no_end) > 0:
        memberships.append(memberships_no_end)
    if len(memberships_ended) > 0:
        memberships.append(memberships_ended)

    context = {
        "person": selected_person,
        "papers": paper,
        "mentioned_in": mentioned,
        "memberships": memberships,
        "subscribable": True,
        "is_subscribed": is_subscribed_to_search(request.user, search_params),
    }
    return render(request, 'mainapp/person.html', context)
