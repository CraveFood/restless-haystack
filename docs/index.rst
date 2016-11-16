=================
restless-haystack
=================

Create a RESTful resource for Haystack_-based searches in Django_, using the
lightweight Restless_ framework.

.. _Django: http://djangoproject.com/
.. _Haystack: http://haystacksearch.org/
.. _Restless: https://github.com/toastdriven/restless

API Reference
=============

.. toctree::
   :glob:

   reference/*

Release Notes
=============

* v0.2.0 (2016-11-16)

  * Renamed ``HaystackResource`` to ``SearchableResource``. The former is still
    available, but deprecated, and will be removed in the upcoming 0.3.0
    version.

    * Same applies to ``haystack_resource_factory`` and
      ``searchable_resource_factory``, respectively.
  * Added ``SimpleSearchableResource``, which directly emulates the basic
    behaviour of Haystack's ``SearchView``.
  * Added ``AutocompleteSearchableResource``, which extends
    ``SimpleSearchableResource`` with autocomplete support.

* v0.1.0 (2016-03-10)

  * Initial release
  * Added ``HaystackResource``
  * Added ``haystack_resource_factory``

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

