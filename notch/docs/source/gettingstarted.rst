Getting started
===============

Installation
------------

Use easy_install if it's available on your system::

  $ easy_install notch

Alternatively, download the source package, extract it and run::

  $ python ./setup.py install

You'll need to install three final pre-requisites manually. Download
each and then run their ``setup.py`` installer scripts::

  $ curl -O http://www.tornadoweb.org/static/tornado-0.2.tar.gz
  $ svn checkout http://tornadorpc.googlecode.com/svn/trunk/ tornadorpc-read-only
  $ svn checkout http://jsonrpclib.googlecode.com/svn/trunk/ jsonrpclib-read-only
  $ tar zxf tornado-0.2.tar.gz
  $ cd tornado-0.2
  $ sudo python ./setup.py install
  $ cd ../tornadorpc-read-only
  $ sudo python ./setup.py install	
  $ cd ../jsonrpclib-read-only
  $ sudo python ./setup.py install


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

This doesn't test the agent itself, however, so make sure you
configure an agent and run it.  See :doc:`agent`.
