Getting started
===============

System architecture
-------------------

The Notch system is made up of two components. There is an Agent
(server) process, run on one or more computers that will make
connections to your network equipment. Human users and automated
tasks employ client applications that instruct the Agents to
perform work for them and return any results of that work.

For a basic installation, install an Agent, the Notch
Client library, and one or more Client applications.

In an advanced installation, one installs the Agent on
multiple machines, install the Client library and applications on
computers where they need to receive the results (such as their
workstation, or a server used for periodic maintenance).
The Client library can be configured to use specific Agents for
particular network devices to geographically distribute the work on
the devices.  In addition, the client can load balance work between
appropriate Agents to scale horizontally.  This approach has been
used to scale to a global network with tens of thousands of devices.


Installation for new users
--------------------------

.. note::
   If you have an existing Notch or Notch Client installation, you
   will need to perform some additional work to remove the old
   versions before proceeding with the following notes::

   $ pip uninstall notch
   $ pip uninstall notch.client
   $ pip uninstall notch.agent

   You should check your Python site-packages directories after this is
   completed to ensure you do not have any ``notch`` related files
   lying around.


First of all, Notch requires Python 2.6 or 2.7 (it is not expected to work
with Python 3).

Notch is compatible with ``virtualenv``, should you wish to install
it into that. If so, switch into your desired virtual environment now.

If you do not use ``virtualenv``, you will need to
**run the following commands as root**.

Use ``pip`` to install Notch, if it's available on your system.  If it's
not, use ``easy_install`` to install ``pip``::

  $ easy_install pip


To install the Notch Agent (server which connects to routers, but
has no client utilities)::

  $ pip install notch.agent

To install the Notch client library, used by tools like MrCLI_ to connect
to the Notch Agent (and your network equipment)::

  $ pip install notch.client

Once you have completed this step, there is one final required library that
has to be installed manually. Run this command::

  $ pip install -e git+https://github.com/joshmarshall/tornadorpc.git@fda3e0e4#egg=tornadorpc-dev

Confirmation
------------

You should now find the ``notch-agent`` binary installed in your PATH,
and your Python interpreter should find the necessary modules::

  $ python
  Python 2.6.3 (r263:75183, Nov  6 2009, 15:46:51)
  [GCC 4.2.1 (Apple Inc. build 5646) (dot 1)] on darwin
  Type "help", "copyright", "credits" or "license" for more information.
  >>> import notch.agent
  >>>
  >>> # If you installed the notch.client package also,
  >>> import notch.client

This merely checks that the files are installed correctly.

Next steps
----------
Next, you'll want to configure your agent with information about your
network devices and the authentication information used to log into them.
See the :doc:`agent` page for more.

If you're an existing RANCID user, you'll want to see the
:doc:`rancid_quickstart` page.


.. _MrCLI: http://code.google.com/p/mr-cli