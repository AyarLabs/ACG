.. ACG documentation master file, created by
   sphinx-quickstart on Wed Jun  6 14:22:25 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to ACG's documentation!
===============================
Ayar Custom Generator(ACG) is a package that enables full custom layout creation without a grid. It allows a designer to describe layout generation script in the Python language and automate the layout process 

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   quick_start/root
   getting_started/root
   common_use_cases/root
   api/modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Introduction
============
Documentation for available functions and classes can be found at :ref:`modindex`

Arbitrary Cell Generator is a plugin to Berkeley Analog Generator 2.0 (BAG) that enables parametrized
grid-free layout creation. The main goal of ACG is to make it easy to create highly customized layout generators that
may not be possible in BAG due to its requirement to make layouts technology agnostic. In addition, we make it easy
to combine legacy hand-drawn layouts and IP together with new layout generators.

NOTE: ACG is currently in development, and is being slowly cleaned up for open-source consumption, use at your own risk!
