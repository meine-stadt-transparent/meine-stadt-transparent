import json
from datetime import datetime

from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.translation import ugettext as _

from mainapp.models import Organization, Person, Paper
from mainapp.views.utils import handle_subscribe_requests, is_subscribed_to_search, NeedsLoginError


def persons(request):
    """ Shows all members of the default organization, which are made filterable by the parliamentary group
    memberships. """
    pk = settings.SITE_DEFAULT_ORGANIZATION
    organization = get_object_or_404(Organization, id=pk)
    group_type = settings.PARLIAMENTARY_GROUPS_TYPE[0]

    # Find all parliamentary groups that are the main gremium
    crit = Q(organizationmembership__person__organizationmembership__organization__in=[pk])
    parliamentarygroups = Organization.objects.filter(organization_type_id=group_type).filter(crit).distinct()

    members = []
    memberships = organization.organizationmembership_set.all()
    for membership in memberships:
        # Find all the parliamentary groups the current person is in
        crit = Q(organizationmembership__person__in=[membership.person.id], organization_type_id=group_type)
        groups_names = Organization.objects.filter(crit).values_list("name", flat=True)
        groups_ids = Organization.objects.filter(crit).values_list("id", flat=True)
        groups_css_classes = ["organization-" + str(i) for i in groups_ids]

        members.append({
            'id': membership.person.id,
            'name': membership.person.name_without_salutation(),
            'start': membership.start,
            'end': membership.end,
            'role': membership.role,
            'groups_classes': json.dumps(groups_css_classes),
            'groups_names': ', '.join(groups_names),
        })

    context = {
        "current_committee": organization,
        "members": members,
        "parliamentary_groups": parliamentarygroups,
    }
    return render(request, 'mainapp/persons.html', context)


def get_ordered_memberships(selected_person):
    """ Orders memberships so that the active ones are first, those with unknown end seconds and the ended last. """
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
    return memberships


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

    mentioned = []
    for paper_mentioned in Paper.objects.filter(files__mentioned_persons__in=[pk]).order_by('-modified').distinct():
        mentioned.append({"paper": paper_mentioned, "files": paper_mentioned.files.filter(mentioned_persons__in=[pk])})

    memberships = get_ordered_memberships(selected_person)

    context = {
        "person": selected_person,
        "papers": paper,
        "mentioned_in": mentioned,
        "memberships": memberships,
        "subscribable": True,
        "is_subscribed": is_subscribed_to_search(request.user, search_params),
    }
    return render(request, 'mainapp/person.html', context)
