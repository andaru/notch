An Introdution To Notch
=======================

Notch exposes a proxy interface to your network equipment's
command-line interfaces (CLI), and can be accessed from a supplied
Python client library or via JSON-RPCv2_ at ``http://server:port/JSONRPC2``.

Device usually ship with SNMP interfaces that work well for
read-only data (e.g., counters), and fewer ship XML interfaces that
can be used for configuration management. Command-line interfaces
however, are still very commonly-used for configuration activities.
Notch provides a common API for accessing the CLIs of a variety of
router and switch operating systems, so you can use it to do anything
you fancy, such as:

   1. Confiure these network elements with templates based on any data
      source you can dream up.
   2. Audit the turn-up of services you've configured.
   3. Make large scale changes easier and results more certain.

Notch Agents tasks manage connections to device that clients have
requested access to. They help you manage authentication data you use
to connect to devices. What you then do with those connections is up
to you.

The problem
-----------

Tools such as RANCID_ work well for their intended purpose and have
command execution decoupled from collection and parsing
of router configurations, so they can be used to perform other ad-hoc or
regular scripted activities.  Due to the workstation making all login
and command requests being in one location means that they suffer from
a number of problems:

   1. Management stations talking to remote devices often incur
      significant network delay penalties. Networks with a wide
      geographic scope will always have some devices remote
      (latency-wise) from the management station.

   2. Localised network partitions can severe the management station's
      path to the device, requiring the use of altnerate or out-of-band
      access.

   3. Because the low level transport (SSH, telnet) is used directly by
      the client program (e.g., `clogin`), there is no opportunity to
      compress the data if the transport does not explicitly offer this.

   4. Running the same client tool from multiple workstations can 
      generate many connections to the remote device (e.g., when several
      NOC staff attempt connections to the same device).

   5. Device CPUs are often inferior to those on a cheap workstation
      or netbook. SSH session setup may take many seconds. Running
      a few commands on a device and then disconnecting only to reconnect
      with a different client a few moments later is inefficient.

Why Notch?
----------

Notch is designed to solve the above problems by offering a stateless
API, by abstracting communications transport from any commands entered
on them [3], by re-using existing connections where possible [4, 5]
and by being a distributed system [1, 2].

Why the CLI?
------------

Hacking the CLI in the way Notch unashamedly does is not an ideal
solution for all network management problems. Its approach is not to
support all requirements for all devices, but merely to give users
what they are familiar with; the command-line interface.

Using the CLI has some disadvantages, such as hassles involved in
screen-scraping and timing sensitive I/O.

Interestingly, there are hidden advantages to using the CLI.  Vendors
teach their CLI in training courses, and virtually every engineer
interacting with a network device will have used it. With many more
users, CLI bugs tend to get closed more rapidly and a stable interface
already exists.

Components
----------

Notch generalises the systems approach taken by RANCID_, and splits
any complete network management tool up into two components.

There are client programs, written by administrators and developers
such as the reader.  These communicate with the agent via the client
library or other JSON-RPC v2 interfaces, for non-Python clients.

The Notch Agent is a back-end task which receives JSON-RPC requests
from clients. It creates and manages connections on remote networking
devices, executes commands on them and disconnects from the device
automatically after idle timeouts.

.. _RANCID: http://www.shrubbery.net/rancid/
.. _JSON-RPCv2: http://groups.google.com/group/json-rpc/web/json-rpc-2-0