from typing import List

import dateutil.parser
from django.conf import settings
from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.feedgenerator import Enclosure
from django.utils.translation import gettext as _

from mainapp.functions.search import search_string_to_params, MainappSearch, parse_hit
from mainapp.functions.search_notification_tools import params_to_human_string
from mainapp.models import Paper, File


class SearchResultsFeed(Feed):
    description = _("The latest search results.")
    author_name = settings.PRODUCT_NAME

    # noinspection PyMethodOverriding
    def get_object(self, request, query, **kwargs):
        return query

    def title(self, query):
        params = search_string_to_params(query)
        return params_to_human_string(params)

    def link(self, query):
        return reverse("search", args=[query])

    def items(self, query):
        params = search_string_to_params(query)
        main_search = MainappSearch(params, limit=settings.SEARCH_PAGINATION_LENGTH)
        executed = main_search.execute()
        results = [parse_hit(hit, highlighting=False) for hit in executed.hits]
        return results

    def item_title(self, item):
        return item["type_translated"] + ": " + item["name"]

    def item_description(self, item):
        from mainapp.views import paper_description

        if item["type"] == "paper":
            paper = Paper.objects.get(pk=item["id"])
            return paper_description(paper, settings.ABSOLUTE_URI_BASE)

        return ""

    def item_enclosures(self, item) -> List[Enclosure]:
        if item["type"] == "file":
            file = File.objects.get(pk=item["id"])
            url = settings.ABSOLUTE_URI_BASE + reverse("file-content", args=[file.id])
            return [Enclosure(url, str(file.filesize), file.mime_type)]
        return []

    def item_link(self, item):
        return reverse(item["type"], args=[item["id"]])

    def item_pubdate(self, item):
        created = item.get("created")
        if created:
            return dateutil.parser.parse(created)

    def item_updateddate(self, item):
        modified = item.get("modified")
        if modified:
            return dateutil.parser.parse(modified)
