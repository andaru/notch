Changelog
=========

Version 0.4.3 (Jan 20 2011)
---------------------------

    * New device support.
        * Alcatel OmniSwitch (tested on 6855): ``omniswitch``
        * Nortel ESR: ``nortel_esr``
        * Nortel ESU: ``nortel_esu``
        * Nortel/Bay BaySwitch: ``nortel_bay``
    * Harmonise API for telnet, expect+Paramiko transports.


Version 0.4 (Jul 22 2010)
-------------------------

    * New device support.
        * Arbor TMS/CP: ``arbor``
        * Juniper Netscreen: ``netscreen``
    * Provide apache2 ``mod_wsgi`` configuration file example
        * ``mod_wsgi`` deployment is recommended and well tested.
    * ``command()`` responses are always base64 encoded by the Agent.
    * ``get_config()`` implemented for Paramiko devices (e.g., ``junos``).
    * ``download_file`` implemented for Adva FSP and Paramiko devices.


Version 0.3 (May 27 2010)
-------------------------

    * New device support.
        * Alcatel 7750/7450/7210/7705 (TimOS): ``timetra``
        * Movaz/Adva FSP: ``adva_fsp``
        * DASAN/Siemens PON/ONU (running NOS): ``nos``
        * BATM/Telco/Temarc switches (running BiNOS): ``telco``
    * New abstract transport for building device modules based on
      SSHv2 and either exec-sessions or expect'ed login-sessions.
    * Devices can support multiple connection methods.
    * Devices will retry in cases like EOF errors.
    * New ``devices_info`` API method, similar to ``devices_matching``,
      that returns device metadata.
    * Support SSHv2 servers on IOS and Alcatel/Timetra devices.
    * Credential records can set the connection method and auto-enable property.

Version 0.2 (April 3 2010)
--------------------------

    * Initial Cisco IOS device support (telnet only).
    * Connection (client) class can ``kill_all()`` outstanding requests.
    * Client can now query Agent's device inventory (via new
      ``devices_matching`` API method) using a regular expression.
    * Agent error reporting improved.
    * Device modules now live in the notch/agent/devices/ directory.
    * Devices are disconnected when idle (after ``Device.TIMEOUT_IDLE``).
    * Mr. CLI updated significantly and split off into separate package,
      see http://code.google.com/p/mr-cli


Version 0.1 (March 25 2010; initial release)
--------------------------------------------

    * Initial release.
    * JunOS device support (via SSH2 only).

