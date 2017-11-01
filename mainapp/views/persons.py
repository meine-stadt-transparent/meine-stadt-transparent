from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext as _

from mainapp.models import Committee, Person, UserAlert, Paper


def persons(request):
    pk = settings.SITE_DEFAULT_COMMITTEE
    committee = get_object_or_404(Committee, id=pk)

    memberships = committee.committeemembership_set.all()
    parliamentarygroups = []
    members = []
    for membership in memberships:
        pers = membership.person
        groups_ids = []
        groups_css_classes = []
        groups_names = []

        for parlmember in pers.parliamentarygroupmembership_set.all():
            group = parlmember.parliamentary_group
            groups_ids.append(str(group.id))
            groups_css_classes.append("parliamentary-group-%i" % group.id)
            groups_names.append(group.name)
            if group not in parliamentarygroups:
                parliamentarygroups.append(group)

        members.append({
            'id': pers.id,
            'name': pers.name,
            'start': membership.start,
            'end': membership.end,
            'role': membership.role,
            'groups_ids': ','.join(groups_ids),
            'groups_css_classes': ' '.join(groups_css_classes),
            'groups_names': ', '.join(groups_names),
        })

    context = {
        "current_committee": committee,
        "members": members,
        "parliamentary_groups": parliamentarygroups,
    }
    return render(request, 'mainapp/persons.html', context)


def person(request, pk):
    selected_person = get_object_or_404(Person, id=pk)
    search_params = {"person": pk}

    if 'subscribe' in request.POST:
        if request.user:
            if UserAlert.user_has_alert(request.user, search_params):
                messages.info(request, _('You have already subscribed to this person.'))
            else:
                alert = UserAlert()
                alert.user = request.user
                alert.set_search_params(search_params)
                alert.last_match = datetime.now()  # Prevent getting notifications about old entries
                alert.save()
                messages.success(request, _('You will now receive notifications about new documents.'))
        else:
            # @TODO: Redirect to login form
            messages.error(request, 'You need to log in first')

    if 'unsubscribe' in request.POST and request.user:
        alert = UserAlert.find_user_alert(request.user, search_params)
        if alert:
            alert.delete()
            messages.success(request, _('You will no longer receive notifications.'))

    # That will become a shiny little query with just 7 joins
    filter_self = Paper.objects.filter(submitter_persons__id=pk)
    filter_committee = Paper.objects.filter(submitter_committees__committeemembership__person__id=pk)
    filer_group = Paper.objects.filter(submitter_parliamentary_groups__parliamentarygroupmembership__id=pk)
    paper = (filter_self | filter_committee | filer_group).distinct()

    if not request.user.pk:
        is_subscribed = False
    else:
        is_subscribed = UserAlert.user_has_alert(request.user, search_params)

    context = {
        "person": selected_person,
        "papers": paper,
        "is_subscribed": is_subscribed,
    }
    return render(request, 'mainapp/person.html', context)