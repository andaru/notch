# Overview #

Notch is a service that makes it possible to _do stuff_ on routers, switches and other devices supported by it.  But what _stuff_ is possible, and what sets Notch apart from just using SSH, RSH or telnet to connect to routers?

That difference is the simple API provided by this service - by removing the drudge work of managing router connections, your code can just focus on making an API call and doing something useful with the results.  For example, it makes the multi-router CLI,  [Mr.CLI](http://code.google.com/p/mr-cli) able to connect to any device on your network supported by Notch without any additional code.

# Introduction #

The Notch API is offered as a web-service in JSON-RPC (version 2) format.

## Philosophy ##

When one makes a connection to an individual router's CLI, they expect an interactive session between themselves and the router; however, this is not always the case - some devices have a purely command/response interface.

To provide a uniform programming interface, Notch's API simulates a command/response interface to all types of equipment.  In short,

  * The Notch service is effectively a proxy between the programmer and the device.
  * Data communication is between the Notch Agent and the device, so Agents are best placed towards the edge of the network.
  * Connections to devices, where required, are established implicitly - there is no `connect` API call.
  * Similarly, connections are cached where possible, in an attempt to minimise latency and also save device CPU in the case of many small SSH sessions.
  * All response data is `base64` encoded.  See the Note below.

# Notch API Calls #

## Calling convention ##

The API uses JSON-RPC version 2. The argument names given in method envelopes, below, are the exact method names used in the JSON declaration, so in the `command` example below, the arguments is a hash with keys `device_name`, `command` and `mode`.


---


`devices_matching(regexp)`

Queries the Agent for a list of device names matching the regexp.

Arguments:
  * `regexp`: A regular expression in [Python's syntax](http://docs.python.org/howto/regex.html) for the Agent to match against its list of known devices.

Returns:
  * A list of strings, device names.


---


`devices_info(regexp)`

Queries the Agent for information about devices matching the regexp.

Arguments:
  * `regexp`: A regular expression in [Python's syntax](http://docs.python.org/howto/regex.html) for the Agent to match against its list of known devices.

Returns:
  * A hash of devices, keyed by device name of strings, device names.  Values are hashes with the `device_type` (string), `addresses` (list) and `device_name` (string) keys.  The `device_type` value is one of the Notch device model types, such as `cisco`, `juniper`,
> `telco`, `timetra`, etc.


---


`command(device_name, command, mode)`

Executes a command on a remote device, optionally in a certain CLI mode.

Arguments:
  * `device_name`: A string, the host name for the Agent to execute the command on.
  * `command`: A string, the command to execute (e.g., "show interfaces").
  * `mode`: A string, optional. An alternate CLI mode (e.g,. 'system' or 'shell') to execute the command in.  Modes are specific to each device, and are used where the device provides multiple useful execution modes, an example being Juniper, where there is the normal CLI, a Unix Shell and a "system" mode occasionally used for secret engineering commands.

Returns:
  * A string containing the command's response


---


`get_config(device_name, source, mode)`

Gets the specified configuration file from the device.

Arguments:
  * `device_name`: A string, the host name for the Agent to execute the command on.
  * `source`: A string, the filename to retrieve from the device. May be a full path or a "well-known" configuration file name, depending on the device type.  e.g., On a Cisco IOS device, using `startup-configuration` will retrieve the last committed (saved) configuration.
  * `mode`: A string, optional. An alternate CLI mode to execute the command in.


---


`set_config(device_name, destination, data, mode)`

Updates the configuration on the device using the supplied data.

Arguments:
  * `device_name`: A string, the host name for the Agent to execute the command on.
  * `destination`: A string, the filename to update on the remove device.
  * `data`: A string, the configuration data to send to the device.
  * `mode`: A string, optional. An alternate CLI mode to execute the command in.

# Note: Data encoding #

The service will return `base64` encoded data for all methods (this is to support binary responses).  The Notch Python Client Library will decode this for you, but if you are writing your own client implementation that talks JSON-RPC to the Agent, you will need to decode the data yourself, e.g.,

In Perl:

```
  use MIME::Base64;
  $decoded = decode_base64($response);
```

In Python:

```
   import base64

   decoded = base64.b64decode(response)
```

In Java, you have [several library options](http://www.google.com/search?q=java+base64+decode).

In C or C++, there is a [free library available](http://libb64.sourceforge.net/).