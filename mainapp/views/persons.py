import json
from collections import defaultdict
from typing import List

from django.conf import settings
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from mainapp.models import Organization, Person, Paper, Membership, File
from mainapp.views.utils import (
    handle_subscribe_requests,
    is_subscribed_to_search,
    NeedsLoginError,
)


def persons(request):
    """Shows all members of the default organization, which are made filterable by the parliamentary group
    memberships."""
    organization = get_object_or_404(
        Organization, id=settings.SITE_DEFAULT_ORGANIZATION
    )

    members, parliamentarygroups = person_grid_context(organization)

    context = {"members": members, "parliamentary_groups": parliamentarygroups}
    return render(request, "mainapp/persons.html", context)


def get_persons_with_prefetch(group_type, organization):
    """
    We want to know which person is in which parliamentary group. Instead of iterating over the persons directly,
    we're gonna go over memberships, which can carry a start and a end date with them. We then prefetch
    all membership -> person -> their memberships -> parliamentary groups (= organizations with the right type)

    Django does some really awesome stuff then and transforms this into 4 fast queries
    """
    queryset = Membership.objects.filter(
        organization__organization_type_id=group_type
    ).prefetch_related("organization")
    prefetch = Prefetch(
        "person__membership_set", queryset=queryset, to_attr="prefetched_orgs"
    )
    memberships = organization.membership_set.filter(
        Q(end__isnull=True) | Q(end__gt=timezone.now())
    ).prefetch_related(prefetch)
    return memberships


def person_grid_context(organization):
    group_type = settings.PARLIAMENTARY_GROUPS_TYPE[0]

    # Find all parliamentary groups that are in that organization
    crit = Q(membership__person__membership__organization__in=[organization.id])
    parliamentarygroups = (
        Organization.objects.filter(organization_type_id=group_type)
        .filter(crit)
        .distinct()
    )

    memberships = get_persons_with_prefetch(group_type, organization)
    members = []
    for membership in memberships:
        # Find all the parliamentary groups the current person is in
        groups_names = [
            i.organization.short_name for i in membership.person.prefetched_orgs
        ]
        groups_ids = [i.organization.id for i in membership.person.prefetched_orgs]
        groups_css_classes = ["organization-" + str(i) for i in groups_ids]

        members.append(
            {
                "id": membership.person.id,
                "name": membership.person.name,
                "start": membership.start,
                "end": membership.end,
                "role": membership.role,
                "groups_classes": json.dumps(groups_css_classes),
                "groups_names": ", ".join(groups_names),
            }
        )
    return members, parliamentarygroups


def get_ordered_memberships(selected_person: Person) -> List[List[Membership]]:
    """Orders memberships so that the active ones are first, those with unknown end seconds and the ended last."""
    memberships_active = (
        selected_person.membership_set.filter(end__gte=timezone.now().date())
        .prefetch_related("organization")
        .all()
    )
    memberships_no_end = (
        selected_person.membership_set.filter(end__isnull=True)
        .prefetch_related("organization")
        .all()
    )
    memberships_ended = (
        selected_person.membership_set.filter(end__lt=timezone.now().date())
        .prefetch_related("organization")
        .all()
    )
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
        handle_subscribe_requests(
            request,
            search_params,
            _("You will now receive notifications about new documents."),
            _("You will no longer receive notifications."),
            _("You have already subscribed to this person."),
        )
    except NeedsLoginError as err:
        return redirect(err.redirect_url)

    filter_self = Paper.objects.filter(persons__id=pk)
    filter_organization = Paper.objects.filter(organizations__membership__person__id=pk)
    paper = (filter_self | filter_organization).distinct()
    memberships = get_ordered_memberships(selected_person)

    mentioned = defaultdict(list)
    files_mentioned = File.objects.filter(mentioned_persons__in=[pk]).prefetch_related(
        "paper_set"
    )
    for file_mentioned in files_mentioned:
        for paper_mentioned in file_mentioned.paper_set.all():
            mentioned[paper_mentioned].append(file_mentioned)

    # The template doesn't like defaultdicts
    mentioned = dict(mentioned)

    context = {
        "person": selected_person,
        "papers": paper,
        "mentioned_in": mentioned,
        "memberships": memberships,
        "subscribable": True,
        "is_subscribed": is_subscribed_to_search(request.user, search_params),
        "to_search_url": reverse("search", args=["person:" + str(selected_person.id)]),
    }
    return render(request, "mainapp/person.html", context)
