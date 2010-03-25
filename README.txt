Notch
=====

Notch brings a programmatic interface to all your network equipment
like switches, routers and firewalls.  Its Agent manages the
command-line interfaces of network equipment in your network so that
you can write powerful network management applications using the
included Python library or from other languages by using the JSON-RPC
interface.

For example, to get the version information from every device on your
network (via a Notch Agent running at ``localhost:8080``)::

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

Use either easy_install::

    $ easy_install notch

or if you have downloaded the package already::

    $ python ./setup.py install


Configuration
-------------

The Notch Agent requires some configuration to get started, and things
are easiest if you already use the RANCID system, as the Notch Agent
will read its configuration files to populate its inventory.  

Then, you can start a Notch Agent using the following::

    $ notch-agent --config=/path/to/your/notch.yaml
