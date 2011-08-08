Getting started
===============

Installation
------------

Use pip to install Notch, if it's available on your system.

To install the Notch Agent (server which connects to routers, but
has no client utilities)::

  $ pip install notch

To install the Notch client library, used by tools like MrCLI_ to connect
to the Notch Agent (and your network equipment)::

  $ pip install notch.client

If pip is not installed, but easy_install is, install it first, then Notch::

  $ easy_install pip
  $ pip install notch

Do NOT use easy_install to install the Notch agent (or client library),
as there is a bug here which will disable the client library.

Alternatively, download the Notch source package, extract it and run::

  $ python ./setup.py install

This should install other pre-requisites, such as the Tornado framework
and JSON-RPC library.

You'll need to install one final pre-requisite manually.  Download it
and then run the ``setup.py`` installer script::

  $ git clone https://github.com/joshmarshall/tornadorpc.git
  $ cd ./tornadorpc
  $ sudo python ./setup.py install

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

This doesn't test the agent itself, however, so make sure you
configure an agent and run it.  See :doc:`agent`.

N.B., If you installed notch.client and you get an error message stating
the 'client' module cannot be found, use pip to uninstall notch and then
reinstall it with pip, as so::

  $ echo y | pip uninstall notch
  $ pip install notch

.. _MrCLI: http://code.google.com/p/mr-cli
