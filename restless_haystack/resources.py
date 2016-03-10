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
    """
    A ``DjangoResource`` subclass specialized in Haystack searches.
    The ``form_class``, ``load_all`` and ``searchqueryset`` properties work
    the same as their Haystack view counterparts.

    The ``prepare`` function is applied to the search results.
    """
    form_class = SearchForm
    searchqueryset = None
    load_all = True

    def list(self):
        """
        Returns the results of a Haystack search, whose query is given by the
        ``q`` parameter (and, optionally, ``page``).

        :returns: A dictionary containing the resulting page, the original
         query and a collection of suggestions, if applicable
        :rtype: dict
        """
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
        """
        Serializes the search results returned by ``list``. The output contains
        the following fields:

        * ``objects``: a list of prepared results (same as ``Resource``)
        * ``page``: number of the returned page
        * ``start_index``: initial (1-based) index for the returned page
        * ``end_index``: final (1-based) index for the returned page
        * ``num_pages``: total number of pages
        * ``query``: the provided query
        * ``suggestion``: a suggestion, if applicable

        :param data: The search data to serialize
        :type data: dict

        :returns: The serialized body
        :rtype: string
        """
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
    """
    A factory for creating ``HaystackResource`` subclasses with the given
    properties.

    :return: A ``HaystackResource`` subclass
    """
    class Resource(HaystackResource):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.searchqueryset = searchqueryset
            self.form_class = form_class
            self.load_all = load_all
    return Resource
