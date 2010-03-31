Getting started
===============

Installation
------------

Use easy_install if it's available on your system::

  $ easy_install notch

Alternatively, download the source package, extract it and run::

  $ python ./setup.py install

Confirmation
------------

You should now find the ``notch-agent`` binary installed in your PATH,
and your Python interpreter should find the necessary modules::

  $ python
  Python 2.6.3 (r263:75183, Nov  6 2009, 15:46:51) 
  [GCC 4.2.1 (Apple Inc. build 5646) (dot 1)] on darwin
  Type "help", "copyright", "credits" or "license" for more information.
  >>> import notch.client
  >>> import notch.agent
  >>>


RANCID quickstart
-----------------

If you already have RANCID_ installed, you can get started in a couple
of minutes.

In the example, we'll keep our Notch configuration in ``/usr/local/etc``.

First, find the directory that has directories with ``router.db``
files in them. For example::

  /var/local/rancid/

  Containing, for example, these ``router.db`` files::

    /var/local/rancid/access/router.db
    /var/local/rancid/backbone/router.db
    /var/local/rancid/mgmt/router.db

Use this ``notch.yaml`` configuration file (given the path above)::

  device_sources:
    rancid_configs:
        provider: router.db
        root: /var/local/rancid/
        ignore_down_devices: True

  options:
    credentials: /usr/local/etc/notch-credentials.yaml

Next, create the ``/usr/local/etc/notch-credentials.yaml`` file. This
is site-specific, but here's an example of the types of things you can
express::

  - regexp: ^acc[0-9]+.*
    username: administrator
    password: notCisc0
    enable_password: l3ssLike7y
  - regexp: .*
    username: administrator
    password: s4meOlth4nG

Devices like ``acc1.bne`` and ``acc400.mel`` will use the first credential,
while all other devices will use the second credential.

.. note:: A ``regexp: .*`` wildcard record is not required. Your
   agents will fail closed in this case.  This is a recommended
   security precaution.

Start the ``notch-agent`` (a Tornado webserver running the Notch
application, with a threadpool handling slow I/O) to answer requests::

  $ notch-agent --config=/usr/local/etc/notch.yaml --logging=debug

That's it, you now have a Notch Agent running on ``localhost:8080``!

You can even test the client from within the Python interactive
interpreter::

   $ python
   Python 2.6.3 (r263:75183, Nov  6 2009, 15:46:51) 
   [GCC 4.2.1 (Apple Inc. build 5646) (dot 1)] on darwin
   Type "help", "copyright", "credits" or "license" for more information.
   >>> import notch.client
   >>> n = notch.client.Connection('localhost:8080')
   >>> all_devices = n.devices_matching('^.*$')
   >>> print len(all_devices)
   2
   >>> def cb(r):
   ...   print str(r)
   ... 
   >>> for dev in all_devices:
   ...   n.command(dev, 'show version and blame', callback=cb)
   ... 
   >>> n.wait_all()
   <notch.client.client.Request object at 0x10193c510>
   <notch.client.client.Request object at 0x1019091d0>
   >>> 

Now try out the ``mrcli`` client (in ``notch/mrcli/mrcli.py``)
for a more complete example.

.. _RANCID: http://www.shrubbery.net/rancid/