Notch Agent
===========

The Notch Agent is the HTTP/JSON-RPC server at the core of the Notch
system.  Run one or more copies (aka *tasks*) of the agent binary or
WSGI application, referring to the same configuration data (the
configuration and credentials data files).

Clients refer to these agent tasks by the address/hostname and port of the
Agent HTTP servers, like ``notch.example.com:8443`` or
``notch.example.com:8080``.

The included Python client library can handle load balancing between 
multiple agent tasks.  See ``notch/client/lb_transport.py`` and
``notch/client/client.py`` (the client library itself) for details
on how to select different load-balancing strategies (advanced users only).

Standalone and WSGI applications
--------------------------------
The Notch Agent is distributed as an application using the Tornado_
web-server, or as a Python WSGI application function.

Stand alone
"""""""""""

The standalone server (``notch-agent`` should be in your ``PATH``) can
be used for testing or production if you have no desire for WSGI server
infrastructure.  Start it with the ``--config`` argument pointing at your
``notch.yaml`` file::

  $ notch-agent --config=/path/to/notch.yaml --logging=debug

WSGI application
""""""""""""""""

As WSGI servers use differing configuration methods to identify where
the WSGI application code lies, the following data can be used to
craft the necessary configuration for your server.

The module containing the WSGI application is::

  notch.agent.wsgi.application

Which lives in the file (likely in your ``site-packages`` directory)::

  notch/agent/wsgi.py

Running under Spawning
^^^^^^^^^^^^^^^^^^^^^^

To run Notch under the Spawning_ HTTP server, for example, you can use
this script to run four servers running agent tasks (thus minimising
CPython GIL issues)::

  #!/bin/bash
  PORTS = "8080 8081 8082 8083"
  for PORT in ${PORTS}
  do
    NOTCH_CONFIG=/path/to/your/notch.yaml spawn -d -p $PORT -s 2 -t 50 -u notchuser
  done

Environment variables
---------------------

The following environment variables are used to influence the Notch system
at client or agent start-up time.

.. note:: The ``NOTCH_CONFIG`` variable must be set, pointing
          at the agent configuration file, prior to
          initialising the WSGI application.  It has no effect
          when	 using ``notch-agent``, which takes a
          ``--config`` argument, instead.

.. table::

   ==================== ======= ================================================
   Environment variable Used by Description
   ==================== ======= ================================================
   NOTCH_CONFIG         Server  The path to the configuration file 
                                (default: None).
   NOTCH_AGENTS	        Client  A comma-separated list of agent host:port
                                addresses. (default: None).
   NOTCH_CONCURRENCY    Client  The maximum number of requests to keep in flight
                                at any one time (default: 50).
   ==================== ======= ================================================

Client can programatically define which agents and concurrency they would prefer
with the ``agents=`` and ``max_concurrency=`` arguments to the 


Agent configuration
-------------------

Master configuration
""""""""""""""""""""

The Agent requires a configuration file, which is in YAML_ format.

There are two required top level sections, ``device_sources`` and ``options``.

``options`` contains the ``credentials`` attribute used to define the
path to your credentials configuration file. In the ``device_sources``
section you can configure multiple device sources, which allow

Example
"""""""

e.g., ``/usr/local/etc/notch.yaml``::

  device_sources:
      source1:
          provider: router.db
          root: /path/to/your/rancid_root_dir
          ignore_down_devices: True

  options:
      credentials: /path/to/your/notch-config/credentials.yaml

The ``provider`` attribute has two currently accepted values:

  ``router.db``: Loads device information (device names and vendor
  module type) from RANCID router.db_ configuration files.  The agent
  asynchronously refreshes its data every few minutes.

  ``dnstxt``: Use DNS A queries to find IP address information, and
  DNS TXT queries to retrieve ``v=notch1`` prefixed records for the
  purpose of determining vendor module type information for the
  device, e.g.,

::

    ar1.foo.int.example.com. IN A   10.0.22.75
    ar1.foo.int.example.com. IN TXT "v=notch1 device_type=juniper"


Credentials file
^^^^^^^^^^^^^^^^

User credentials, that is the usernames, passwords or SSH keys used when
connecting to network devices, are configured in the credentials configuration
file.

  If you haven't already, you should now go and create Notch specific
  users (e.g., ``automation``) on your administrative TACACS+ or
  RADIUS server.  Change the passwords on the server and in your
  credentials configuration file on a regular basis.

.. note:: 

  Only a limited range of system administrators need know these
  passwords. Make sure you set the permissions on your password file
  appropriately::

    $ chown notchuser /opt/local/etc/notch.yaml
    $ chmod 700 /opt/local/etc/notch.yaml

Credential Attributes
"""""""""""""""""""""

The credentials file is a YAML repeated block, consisting of
attributes named ``regexp``, ``username``, ``password``,
``enable_password`` and ``ssh_private_key``.  

``regexp`` is a string regular expression. Device names matching this
regular expression will be use this credential.  For each request, the
filter is evaluated in `Last Match`__ mode.  Start with any rules that
match an individual device, followed by those which match by less
restrictive regular expressions.  If you require one, place any
``regexp: .*`` defaults at the end of the configuration file.

``username`` and ``password`` should be understood,
``enable_password`` is the "enable" password often used on Cisco or
other platforms supporting TACACS+.  ``ssh_private_key`` is an ASCII-armored
form of the SSH private key data used for matching devices.

Example credentials file
""""""""""""""""""""""""

In the example below, the border routers (e.g., ``br01.bne03``, ``br1.mel07``)
will use the ``automation`` username with the ``tBRpass`` and the predictable
enable password.  Every other device will use the ``ssh_private_key``, whilst
stil using the ``automation`` username.

``credentials.yaml``::

  -
    regexp: ^br[0-9].*
    username: automation
    password: tBRpass
    enable: c15c0
  -
    regexp: .*
    username: automation
    ssh_private_key: "-----BEGIN RSA PRIVATE KEY-----\n..."

There is *no need* for a trailing ``-`` (it adds an empty block which
is ignored by the parser).

.. _LastMatch: http://www.phildev.net/ipf/IPFques.html#ques2
__ LastMatch_
.. _router.db: http://www.shrubbery.net/rancid/man/router.db.5.html
.. _Spawning: http://pypi.python.org/pypi/Spawning/
.. _Tornado: http://www.tornadoweb.org/
.. _YAML: http://yaml.org/spec/1.2/spec.html

