
ChemExpoDB: Factotum
======================================

.. role:: bash(code)
   :language: bash

Sphinx templates updated from model with :bash:`sphinx-apidoc --force --follow-links -d 3 -o ./autodoc .. ../dashboard/migrations ../dashboard/tests`
Refresh the documents with :bash:`./docs/make html`

.. toctree:: stubs
   :maxdepth: 3

   modules/dashboard/models
   modules/dashboard/utils
   modules/dashboard/views

   modules/bulkformsets



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
