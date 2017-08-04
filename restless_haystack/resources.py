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


class SearchableResource(SearchView, DjangoResource):
    """
    A RESTful resource which applies Haystack's ``SearchView`` when listed,
    including the use of ``SearchForm`` and subclasses for validation.

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
            'per_page': self.results_per_page,
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


class PrepareIndexDeprecationMetaClass(type):
    def __new__(meta, name, bases, dct):
        # Remove prepare_indexes from class attributes replace
        #   it by a property (getter and setter)
        prepare_indexes = dct.pop('prepare_indexes', None)
        dct['prepare_indexes'] = meta.prepare_indexes

        # create the class
        cls = type.__new__(meta, name, bases, dct)

        # if prepare_indexes was initialy set and use_model_instances
        #   was unset use the given prepare_indexes value
        if prepare_indexes and not getattr(meta, 'use_model_instances', None):
            cls.prepare_indexes = prepare_indexes
        return cls

    @property
    def prepare_indexes(meta):
        warnings.warn(DEPRECATION_MESSAGE.format(
            'prepare_indexes', 'use_model_instances'), DeprecationWarning)
        # since prepare_indexes and use_model_instances have opposite
        #   meanings revert it before returning
        return not meta.use_model_instances

    @prepare_indexes.setter
    def prepare_indexes(meta, value):
        warnings.warn(DEPRECATION_MESSAGE.format(
            'prepare_indexes', 'use_model_instances'), DeprecationWarning)
        # since prepare_indexes and use_model_instances have opposite
        #   meanings revert it before storing
        meta.use_model_instances = not value


class SimpleSearchableResource(DjangoResource,
                               metaclass=PrepareIndexDeprecationMetaClass):
    """
    A RESTful resource which takes a ``SearchQuerySet`` from Haystack, filters
    it and returns a paginated list.
    """

    search_filters = []
    results_per_page = RESULTS_PER_PAGE
    load_all = False
    #: Whether to use the actual model instead of its ``SearchIndex``.
    use_model_instances = False
    page_attribute_name = 'page'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not getattr(self, 'searchqueryset', False):
            self.searchqueryset = SearchQuerySet()

    def list(self):
        filters = {attr: self.request.GET[attr] for attr in self.search_filters
                   if attr in self.request.GET}
        self.searchqueryset = self.searchqueryset.filter(**filters)
        self.filter_query()
        if self.load_all:
            self.searchqueryset = self.searchqueryset.load_all()
        return self.searchqueryset

    def filter_query(self):
        if self.request.GET.get('q'):
            self.searchqueryset = self.searchqueryset.filter(
                content=self.request.GET.get('q'))

    def get_page(self, data):
        try:
            page_no = int(self.request.GET.get(self.page_attribute_name, 1))
        except (TypeError, ValueError):
            raise NotFound('Invalid page number.')
        if page_no < 1:
            raise NotFound('Page number should be 1 or greater.')
        # Explicitly evaluate data before sending it to Paginator, otherwise
        # (at least in the case of RelatedSearchQuerySet) the total count
        # goes completely wrong
        # see: https://github.com/django-haystack/django-haystack/issues/362
        data[:self.results_per_page]
        paginator = Paginator(data, self.results_per_page)

        try:
            page = paginator.page(page_no)
        except InvalidPage:
            raise NotFound('No such page!')
        return page

    def serialize_list(self, data):
        """Serializes the search results."""

        if self.results_per_page:
            self.page = self.get_page(data)
            data = self.page.object_list

        if self.use_model_instances:
            data = (res.object for res in data)

        return super().serialize_list(data)

    def wrap_list_response(self, data):
        """Adds pagination and query information to search results."""

        response_dict = super().wrap_list_response(data)

        if hasattr(self, 'page'):
            if self.page.has_next():
                next_page = self.page.next_page_number()
            else:
                next_page = None

            if self.page.has_previous():
                previous_page = self.page.previous_page_number()
            else:
                previous_page = None

            response_dict['pagination'] = {
                'num_pages': self.page.paginator.num_pages,
                'count': self.page.paginator.count,
                'page': self.page.number,
                'start_index': self.page.start_index(),
                'end_index': self.page.end_index(),
                'next_page': next_page,
                'previous_page': previous_page,
                'per_page': self.results_per_page,
            }

        response_dict['search'] = {
            'query': self.request.GET.get('q'),
        }
        return response_dict


class AutocompleteSearchableResource(SimpleSearchableResource):
    autocomplete_field = 'content'

    def filter_query(self):
        if self.request.GET.get('q'):
            params = {self.autocomplete_field: self.request.GET.get('q')}
            self.searchqueryset = self.searchqueryset.autocomplete(**params)


def searchable_resource_factory(searchqueryset=None, form_class=SearchForm,
                                load_all=True):
    """
    A factory for creating ``SearchableResource`` subclasses with the given
    properties.

    :return: A ``SearchableResource`` subclass
    """
    class Resource(SearchableResource):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.searchqueryset = searchqueryset
            self.form_class = form_class
            self.load_all = load_all
    return Resource

# set for removal

DEPRECATION_MESSAGE = '`{}` is deprecated; `{}` replaces it.' + \
                      'The old name is set for removal on version 0.3'


class HaystackResource(SearchableResource):
    def __init__(self, *args, **kwargs):
        warnings.warn(DEPRECATION_MESSAGE.format(
            'HaystackResource', 'SearchableResource'),
            DeprecationWarning)
        super().__init__(*args, **kwargs)


def haystack_resource_factory(searchqueryset=None, form_class=SearchForm,
                              load_all=True):
    warnings.warn(DEPRECATION_MESSAGE.format(
        'haystack_resource_factory', 'searchable_resource_factory'),
        DeprecationWarning)
    return searchable_resource_factory(searchqueryset, form_class, load_all)
