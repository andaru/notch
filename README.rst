Notch
=====

Notch brings a programmatic interface to all your network equipment
like switches, routers and firewalls.  Its Agent manages the
command-line interfaces of network equipment in your network so that
you can write powerful network management applications using the
included Python library or from other languages by using the JSON-RPC
interface.

.. note::
   This package provides just the Notch Agent. A basic installation on
   a single machine also requires the client library, available in the
   ``notch.client`` package.

For example, to get the version information from every cisco-ish
device on your network (via a Notch Agent running at ``localhost:8080``)::

    #!/usr/bin/env python

    import notch.client

    def callback(request):
      """Called by the Notch Client when a request is complete."""
      if request.error:
        print 'Exception: ', str.error.__class__.__name__
        print str(request.error)
      else:
        print request.result

    nc = notch.client.Connection('localhost:8080')

    # Gets a list of devices from the Notch Agent.
    try:
      all_devices = nc.devices_matching('^.*$')
    except notch.client.Error:
      print 'Error querying for devices.'
      all_devices = []

    # Send the command to each device, asynchronously receiving results.
    for device in all_devices:
      nc.command(device, 'show version', callback=callback)

    # Wait for all outstanding requests to complete.
    nc.wait_all()


Installation
------------

.. note::
   As of version 0.5, Notch is split into separate ``notch.client``
   and ``notch.agent`` pypi packages sharing a namespace package
   ``notch``.

   Users upgrading from earlier versions must remove all existing Notch
   packages before proceeding with installation::

   $ pip uninstall notch
   $ pip uninstall notch.client
   $ pip uninstall notch.agent

   Also check your Python ``site-packages`` directories to ensure you
   do not have any ``notch*`` files or directories.

Use ``pip`` to install both the Notch Agent or Client library.

You'll need both packages to start with, but in larger installations,
only machines acting as Agents require the ``notch.agent`` package.

    $ pip install notch.agent
    $ pip install notch.client

This will install all but one dependency, which can be then installed using::

    $ pip install -e git+https://github.com/joshmarshall/tornadorpc.git@fda3e0e4#egg=tornadorpc-dev

You can also use ``easy_install``, but we don't recommend that. If you don't
have ``pip``, install it with ``easy_install`` first.

Configuration
-------------

The Notch Agent requires some configuration to get started, and things
are easiest if you already use the RANCID system, as the Notch Agent
will read its router.db configuration file to populate its inventory.

Then, you can start a Notch Agent using the built-in testing server::

    $ notch-agent --config=/path/to/your/notch.yaml

The built-in testing server does not support parallel operation, so you
must use a WSGI compatible server for production operation.  Apache2 with
``mod_wsgi`` is used for many installations and an example configuration
can be found in ``config/notch-mod_wsgi.sample.conf``.  The WSGI application
object itself is defined in ``wsgi/notch.wsgi``.

