import dateutil.parser
from django.contrib.syndication.views import Feed
from django.urls import reverse

from mainapp.functions.search_tools import search_string_to_params, MainappSearch, parse_hit, \
    params_to_human_string


class SearchResultsFeed(Feed):
    description = "The latest search results."

    def get_object(self, request, query):
        return query

    def title(self, query):
        params = search_string_to_params(query)
        return params_to_human_string(params)

    def link(self, query):
        return reverse('search', args=[query])

    def items(self, query):
        params = search_string_to_params(query)
        main_search = MainappSearch(params)
        executed = main_search.execute()
        results = [parse_hit(hit) for hit in executed.hits]
        return results

    def item_title(self, item):
        return item['type_translated'] + ': ' + item['name']

    def item_description(self, item):
        from mainapp.views import paper_description

        if item['type'] == 'paper':
            return paper_description(item)

        # @TODO: Description for other types, especially files and meetings

        return ''

    def item_link(self, item):
        return reverse(item['type'], args=[item['id']])

    def item_pubdate(self, item):
        return dateutil.parser.parse(item['created'])

    def item_updateddate(self, item):
        return dateutil.parser.parse(item['modified'])
