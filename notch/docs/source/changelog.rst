Changelog
=========
	
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
	
