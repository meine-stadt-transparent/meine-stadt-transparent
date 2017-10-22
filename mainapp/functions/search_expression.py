from enum import Enum

"""
A example JSON would be:
{
  "type": "combination",
  "mode": "OR",
  "terms": [
    {
      "type": "person",
      "id": 23
    },
    {
      "type": "combination",
      "mode": "AND",
      "terms": [
        {
          "type": "keyword",
          "keywor": "term1"
        },
        {
          "type": "keyword",
          "keywor": "term2"
        }
      ]
    }
  ]
}

@TODO: Support negation
"""


class SearchExpression:
    type = str

    @staticmethod
    def create_from_json(json):
        if not json['type']:
            raise Exception('Invalid JSON string passed')

        if json['type'] == 'paper':
            return PaperSearch(json)
        elif json['type'] == 'person':
            return PersonSearch(json)
        elif json['type'] == 'keyword':
            return KeywordSearch(json)
        else:
            raise Exception('Invalid search type: %s' % json['type'])


class SearchMode(Enum):
    AND = 'AND'
    OR = 'OR'


class SearchTermCombination(SearchExpression):
    mode = SearchMode
    terms = []

    def __init__(self, json):
        self.type = 'combination'
        if json['mode'] == 'OR':
            self.mode = SearchMode.OR
        elif json['mode'] == 'AND':
            self.mode = SearchMode.AND
        else:
            raise Exception('Unknown mode: %s' % json['mode'])

        for term in json['terms']:
            self.terms.append(SearchExpression.create_from_json(term))

    def __str__(self):
        names = []
        for term in self.terms:
            names.append(term.__str__())
        return self.mode + ': ' + ', '.join(names)


class PaperSearch(SearchExpression):
    def __init__(self, json):
        self.type = 'paper'
        self.paper_id = json['id']

    def __str__(self):
        return 'Paper: %i' % self.paper_id


class PersonSearch(SearchExpression):
    def __init__(self, json):
        self.type = 'person'
        self.paper_id = json['id']

    def __str__(self):
        return 'Person: %i' % self.paper_id


class KeywordSearch(SearchExpression):
    def __init__(self, json):
        self.type = 'keyword'
        self.keyword = json['keyword']

    def __str__(self):
        return 'Keyword: %i' % self.keyword
