from django.conf import settings
from django.contrib.syndication.views import Feed
from django.utils.translation import ugettext as _

from mainapp.models.paper import Paper
from mainapp.views.feeds.utils import paper_description


class LatestPapersFeed(Feed):
    title = _("Latest papers")
    link = settings.ABSOLUTE_URI_BASE

    def items(self):
        return Paper.objects.order_by('-sort_date')[:20]

    def item_title(self, paper):
        return paper.name

    def item_description(self, item):
        return paper_description(item)

    def item_link(self, paper):
        return paper.get_default_link()

    def item_pubdate(self, paper):
        return paper.created

    def item_updateddate(self, paper):
        return paper.modified
