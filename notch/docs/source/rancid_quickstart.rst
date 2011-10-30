Quickstart for RANCID users
===========================

If you already have RANCID_ installed, you should be able to get Notch
up and running within 30 minutes of downloading the software by following
this guide.


Configuration data 
------------------

In the example, we'll keep our Notch configuration in ``/usr/local/etc``.

First, find the directory that has directories with ``router.db``
files in them. For example::

  /var/local/rancid/

  Containing, for example, these ``router.db`` files::

    /var/local/rancid/access/router.db
    /var/local/rancid/backbone/router.db
    /var/local/rancid/mgmt/router.db

Use this ``notch.yaml`` master configuration file (given the above path)::

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
   Agents will merely fail to connect to devices that don't match
   any other record. Configuring your Agents without wildcard
   authentication records is a recommended security precaution to avoid
   password leakage to other devices.

Converting the ``.cloginrc`` file
---------------------------------

Since you use RANCID_, you'll have a ``.cloginrc`` file you use for
authentication credential data for RANCID.  You can conver that
(manually, at present) to a Notch credentials file, rather than
creating one from scratch as in the above step.

While the cloginrc_ configuration file declares an option (a username,
password or other option) for a glob per line, Notch places all the
options for a group of devices (whose names match a regular
expression) together in its configuration.

Example
"""""""

cloginrc_ file::

  add user ar* {automation}
  add password ar* {/r0zza} {7p-Kz4PsLa01}
  add user ?r* {cisco}
  add password ?r* {foo} {bar}
  add autoenable * 1  # See note

Equivalent Notch credentials file (e.g., ``credentials.yaml``)::

  - regexp: ^ar.*
    username: automation
    password: "/r0zza"
    enable_password: 7p-Kz4PsLa01
  - regexp: ^.r.*
    username: cisco
    password: foo
    enable_password: bar

.. note:: IOS devices (i.e., any using device module ``dev_ios``)
   presently always ``autoenable`` in Notch.  Allowing configuration
   of this and many other cloginrc type directives in the credentials
   file is coming in a near future release.
   

Running the agent
-----------------

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

If you want a full-featured command-line front-end for Notch, please
try MrCLI_.

.. _RANCID: http://www.shrubbery.net/rancid/
.. _MrCLI: http://code.google.com/p/mr-cli
.. _cloginrc: http://www.shrubbery.net/rancid/man/cloginrc.5.html