An Introdution To Notch
=======================

Notch exposes a programmatic interface to your network equipment, such
as routers, switches, firewalls and load-balancers.  Offering an HTTP
based API and an Agent task which logs into devices, it can provide a
consistent API for just any device that provides a command-line interface.
Notch can be scripted using an available  `Python client library`_, and
other language interfaces can be built using the Agent's JSON-RPC_ API.

Device usually ship with SNMP interfaces that work well for
read-only data (e.g., counters), and fewer ship XML interfaces that
can be used for configuration management. Command-line interfaces
however, are still very commonly-used for configuration activities.
Notch provides a common API for accessing the CLIs of a variety of
router and switch operating systems, so you can use it to do anything
you fancy, such as:

   1. Configure network elements with templates based on any data
      source you can dream up.
   2. Audit the turn-up of services you've configured.
   3. Make large scale changes easier and results more certain.
   4. Have a CLI for large (or small) networks talking to many routers at once.

Notch Agents tasks manage connections to device that clients have
requested access to, keeping connections open until idle, to minimise login
delays.

What you do with the connections made is up to you.

The problem
-----------

Tools like RANCID_ work very well for their intended purpose and have
command execution decoupled from collection and parsing of router
configurations, so they can be used to perform other ad-hoc or
regular scripted activities. They are normally run on an operator's
workstation or from a management server, often in one corner of the
network. As a result, a number of problems exist:

   1. Management stations talking to remote devices often incur
      significant network delay penalties. Networks with a wide
      geographic scope will always have some devices remote
      (latency-wise) from the management station.

   2. Localised network partitions can severe the management station's
      path to the device, requiring the use of alternate or out-of-band
      access.

   3. Because the low level transport (SSH, telnet) is used directly by
      the client program (e.g., `clogin`), there is no opportunity to
      compress the data if the transport does not explicitly offer this.

   4. Running the same tool from multiple workstations generates
      many connections to the remote device (e.g., when several NOC
      staff attempt connections to the same device during an outage).
      Re-using a connection for operators with equal privilege minimises
      this problem.

   5. Some device CPUs are inferior to those on a cheap workstation.
      SSH session setup may take many seconds. Running a few commands on
      a device and then disconnecting only to reconnect with a different
      client soon after is inefficient.

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

There is the Notch Agent (server), run on one or more computers that
will make connections to your network equipment.

Human users and automated tasks employ Notch Client applications
that instruct the Agents to perform work for them and return any
results of that work.

The Notch Agent and Client communicate via HTTP using a JSON-RPC_ API.

For a basic installation, you install an Agent, the Notch
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

.. _RANCID: http://www.shrubbery.net/rancid/
.. _JSON-RPC: http://groups.google.com/group/json-rpc/web/json-rpc-2-0
.. _Python client library: http://pypi.python.org/pypi/notch.client