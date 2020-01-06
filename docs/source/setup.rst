Setup
=====

First things first, make sure have the correct version of hive. For
a list of versions and descriptions, see the
`releases page <https://github.nrel.gov/MBAP/hive/releases/>`_. You can download
the source code directly or use :code:`git` for more robust versioning.

Once you have the source code on your computer you'll need to make sure
you have the right packages installed. An easy way to do this is to use conda
which can be obtained here:

* https://www.anaconda.com/download/ (anaconda)
* https://conda.io/miniconda.html (miniconda)

To build the environment simply run:

.. code-block::

    > conda env create -f environment.yml

Then, activate the environment with:

.. code-block::

    > conda activate hive

That's it! Check out the :doc:`/user_guide/getting_started`
page for instructions on how to get hive up and running.
