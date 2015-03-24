# Notch #
### Making things happen on your network equipment ###

---

## What is it? ##
Notch is web service and (Python) client library which makes it easy to _do stuff_ on your switches, routers and other network equipment. You can use it to build powerful, automated network management applications. It can support anything with a command-line interface and provides a consistent API for multi-vendor access.

## What can I do with it? ##
Supporting the command-line (craft) interfaces of  equipment from leading network equipment vendors, Notch makes it easy to build applications that support multiple vendors out of the box.  Just about anything you can do in the vendor CLI you can do with Notch.

Applications like:
  * automated network provisioning,
  * live network state audit,
  * N-way command-line interface (like [Mr. CLI](http://code.google.com/p/mr-cli))
  * RANCID-style network configuration backup (check out [such a complementary tool for Notch](http://code.google.com/p/punc)).

are now possible with the developer able to treat network device command-line interfaces with a request-response interface.

Notch owes its legacy (though not its code) to the [RANCID project](http://shrubbery.net/rancid/).  It's available as a Python [WSGI](http://wsgi.org/wsgi/) web application or as a stand-alone [Tornado](http://www.tornadoweb.org) web application and provides a HTTP/JSON-RPC v2 interface to allow it to be easily distributed across your network, improving availability and reducing latency issues in large networks.

## Example ##

Using a local or remote Notch Agent, you can [execute commands on any routers matching a particular regular expression](http://code.google.com/p/mr-cli):

```
$ mrcli localhost:8080 --target "^[abc]r.*" --cmd "show ip ospf nei | i [0-9]+"
cr1.mel:
10.100.0.3        0   FULL/  -        00:00:31    192.168.0.7     POS3/0
10.100.0.33       0   FULL/  -        00:00:33    192.168.0.1     GigabitEthernet1/0

br1.mel:
10.100.0.2        0   FULL/  -        00:00:32    192.168.0.4     GigabitEthernet1/0

ar1.mel:
10.100.0.1        0   FULL/  -        00:00:37    192.168.0.0     GigabitEthernet1/0

```


## Getting started ##

Use ```easy_install``` or ``pip install`` to install the Notch package from the [Python Package Index](http://pypi.python.org/pypi).  e.g.,

```
  $ easy_install -U notch
```

Notch has a few other dependencies from packages not in the package index (such as Tornado), which must be installed manually. See the [installation documentation](http://www.enemesco.net/notch/gettingstarted.html) for more.

## Status ##

The project is under development particularly in the areas of device support (recent changes [include](http://code.google.com/p/notch/source/detail?r=bc5bbef3a5da91124c685152f22a46a834c7bc10) [support](http://code.google.com/p/notch/source/detail?r=9d3d24b1362357747098ea048178b3dc87784ad9) for new devices.

Core APIs are relatively mature and breakage is minimal.

The project has currently produced:
  * The [Notch Agent](http://code.google.com/p/notch/source/browse/notch/agent/) web application, or back-end.  Which includes:
    * JunOS / UNIX device support (connections via SSH2).
    * Cisco IOS-style device support (connections via Telnet).
    * BATM/Telco BiNOS, Alcatel/Timetra TiMOS and DASAN/Siemens (ONU) are available in the source repository (will available in the next major release).
  * A Python [client library](http://code.google.com/p/notch/source/browse/notch/client/client.py) to the web-service, with asynchronous operation, and RPC load-balancing.

Other than any additional specific device support you require, you can begin building applications today.

## Tools available ##

These are the actual user-facing tools that use Notch infrastructure to get work done for users.

Available now:
  * [Mr. CLI](http://code.google.com/p/mr-cli), a multi-router command-line interface.

Under development:
  * Router output parsers (to be used by the multi-router CLI for CSV output of "show" commands).
  * A network auditing engine.

If you're interested in asking for a specific feature or device support in the Agent, please join the `notch-dev` mailing list listed on this page and mail your request there.

## Documentation ##
Start at http://notchagent.readthedocs.org/en/latest/gettingstarted.html#

## Developers ##

If you'd like to contribute or have devices you'd like to see supported, please join the `notch-dev` mailing list and introduce yourself.