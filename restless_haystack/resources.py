# coding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import warnings

from django.core.paginator import Paginator, InvalidPage
from haystack.forms import SearchForm
from haystack.query import SearchQuerySet
from haystack.views import SearchView, RESULTS_PER_PAGE
from restless.dj import DjangoResource
from restless.exceptions import NotFound


class SearchResource(SearchView, DjangoResource):
    """
    A RESTful resource which behaves like Haystack's ``SearchView``, including
     the use of ``SearchForm`` (and subclasses) for validation.
    The ``form_class``, ``load_all`` and ``searchqueryset`` properties work
    the same as their ``SearchView`` counterparts.
    """

    def list(self):
        return self(self.request)

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

    def create_response(self):
        (paginator, page) = self.build_page()

        context = {
            'query': self.query,
            'form': self.form,
            'page': page,
            'paginator': paginator,
            'suggestion': None,
        }

        if (self.results and hasattr(self.results, 'query') and
                self.results.query.backend.include_spelling):

            context['suggestion'] = self.form.get_suggestion()

        context.update(self.extra_context())
        return context


class SimpleSearchResource(DjangoResource):
    searchqueryset = SearchQuerySet()
    filters = []
    results_per_page = RESULTS_PER_PAGE
    load_all = False

    def list(self):
        filters = {attr: self.request.GET[attr] for attr in self.filters
                   if attr in self.request.GET}
        self.searchqueryset = self.searchqueryset.filter(**filters)

        if self.request.GET.get('q'):
            self.searchqueryset = self.searchqueryset.filter(
                content=self.request.GET.get('q'))

        if self.load_all:
            self.searchqueryset = self.searchqueryset.load_all()
        return self.get_page()

    def get_page(self):
        try:
            page_no = int(self.request.GET.get('page', 1))
        except (TypeError, ValueError):
            raise NotFound('Invalid page number.')
        if page_no < 1:
            raise NotFound('Page number should be 1 or greater.')
        paginator = Paginator(self.searchqueryset, self.results_per_page)

        try:
            page = paginator.page(page_no)
        except InvalidPage:
            raise NotFound('No such page!')
        return page

    def serialize_list(self, data):
        """
        Serializes the search results returned by ``get_page``. The output
         contains the following fields:

        * ``objects``: a list of prepared results (same as ``Resource``)
        * ``page``: number of the returned page
        * ``start_index``: initial (1-based) index for the returned page
        * ``end_index``: final (1-based) index for the returned page
        * ``num_pages``: total number of pages
        * ``query``: the provided query

        :param data: The resulting search page
        :type data: Page

        :returns: The serialized body
        :rtype: string
        """
        if data is None:
            return ''

        final_data = {
            'objects': [self.prepare(obj) for obj in data.object_list],
            'page': data.number,
            'start_index': data.start_index(),
            'end_index': data.end_index(),
            'num_pages': data.paginator.num_pages,
            'query': self.request.GET.get('q'),
        }
        return self.serializer.serialize(final_data)


def search_resource_factory(searchqueryset=None, form_class=SearchForm,
                            load_all=True):
    """
    A factory for creating ``SearchResource`` subclasses with the given
    properties.

    :return: A ``SearchResource`` subclass
    """
    class Resource(SearchResource):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.searchqueryset = searchqueryset
            self.form_class = form_class
            self.load_all = load_all
    return Resource

# set for removal

DEPRECATION_MESSAGE = '`{}` is deprecated; `{}` replaces it.' + \
                      'The old name is set for removal on version 0.3'


class HaystackResource(SearchResource):
    def __init__(self, *args, **kwargs):
        warnings.warn(DEPRECATION_MESSAGE.format(
            'HaystackResource', 'SearchResource'),
            DeprecationWarning)
        super().__init__(*args, **kwargs)


def haystack_resource_factory(searchqueryset=None, form_class=SearchForm,
                              load_all=True):
    warnings.warn(DEPRECATION_MESSAGE.format(
        'haystack_resource_factory', 'search_resource_factory'),
        DeprecationWarning)
    return search_resource_factory(searchqueryset, form_class, load_all)
