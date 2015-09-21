OOpgrade API
============

The OpenUpgrade library contains all kinds of helper functions for your pre and
post scripts, in OpenUpgrade itself or in the migration scripts of your own
module (in either major or minor version upgrades). It can be installed with

.. code-block:: bash

   pip install oopgrade

and then used in your scripts as

.. code-block:: python

   from oopgrade import oopgrade

General methods
---------------

.. automodule:: oopgrade.oopgrade
   :members:

Version
-------

.. automodule:: oopgrade.version
   :members:
