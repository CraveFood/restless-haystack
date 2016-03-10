# coding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from django.conf import settings
from django.core.paginator import InvalidPage, Paginator

from haystack.forms import SearchForm
from restless.dj import DjangoResource
from restless.exceptions import BadRequest, NotFound

RESULTS_PER_PAGE = getattr(settings, 'HAYSTACK_SEARCH_RESULTS_PER_PAGE', 20)


class HaystackResource(DjangoResource):
    form_class = SearchForm
    searchqueryset = None
    load_all = True

    def list(self):
        results_per_page = self.request.GET.get('per_page') or RESULTS_PER_PAGE

        form = self.form_class(self.request.GET,
                               searchqueryset=self.searchqueryset,
                               load_all=self.load_all)
        if not form.is_valid():
            raise BadRequest(form.errors)
        query = form.cleaned_data['q']
        results = form.search()

        paginator = Paginator(results, results_per_page)
        try:
            page = paginator.page(int(self.request.GET.get('page', 1)))
        except InvalidPage:
            raise NotFound('Invalid page number')

        context = {
            'page': page,
            'query': query,
            'suggestion': None,
        }
        if results.query.backend.include_spelling:
            context['suggestion'] = form.get_suggestion()
        return context

    def serialize_list(self, data):
        if data is None:
            return ''
        final_data = {
            'objects': [self.prepare(obj) for obj in data['page'].object_list],
            'page': data['page'].number,
            'start_index': data['page'].start_index(),
            'end_index': data['page'].end_index(),
            'num_pages': data['page'].paginator.num_pages,
            'query': data['query'],
            'suggestion': data['suggestion'],
        }
        return self.serializer.serialize(final_data)


def haystack_resource_factory(searchqueryset=None, form_class=SearchForm,
                              load_all=True):
    class Resource(HaystackResource):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.searchqueryset = searchqueryset
            self.form_class = form_class
            self.load_all = load_all
    return Resource
