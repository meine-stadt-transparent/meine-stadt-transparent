from django.conf import settings
from django.contrib.syndication.views import Feed
from django.utils.translation import gettext as _

from mainapp.models.paper import Paper
from mainapp.views.feeds.utils import paper_description


class LatestPapersFeed(Feed):
    title = "{}: {}".format(settings.PRODUCT_NAME, _("Latest papers"))
    link = settings.ABSOLUTE_URI_BASE
    description = _("The latest paper")
    author_name = settings.PRODUCT_NAME

    def items(self):
        return Paper.objects.order_by("-sort_date")[:20]

    def item_title(self, paper):
        return paper.name

    def item_description(self, item):
        return paper_description(item, settings.ABSOLUTE_URI_BASE)

    def item_link(self, paper):
        return paper.get_default_link()

    def item_pubdate(self, paper):
        return paper.created

    def item_updateddate(self, paper):
        return paper.modified
