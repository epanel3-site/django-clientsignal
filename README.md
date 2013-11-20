Django Client Signals
=====================

This is an experiment and proof-of-concept at the moment. I really don't 
recommend using it for anything serious. 

Django Client Signals is a SockJS-Tornado-based mechanism for sending
and receiving Django signals as client-side events.

**Table of Contents**

- [Installation](#installation)
- [Requirements](#requirements)
- [Usage Example](#usage-example)
- [Configuration Options](#configuration-options)
    - [Signal Connections](#signal-connections)
    - [Backends](#backends)
    - [Object Encoding](#object-encoding)
    - [SockJS](#sockjs)
- [Commands](#commands)
- [Stats](#stats)
- [Miscellaneous Features](#miscellaneous-features)
    - [Authentication](#authentication)
    - [Caching Middleware](#caching-middleware)
- [TODO](#todo)
- [From Tornadio2](#from-tornadio2)

Installation
------------

To install `django-clientsignal` run:

    pip install git+https://github.com/gulielmus/django-clientsignal.git
    
    django-clientsignal

And add `clientsignal` to your `INSTALLED_APPS`:

    INSTALLED_APPS = (
        ...
        'clientsignal',
    )

Requirements
------------

- `sockjs-tornado`
- `tornado-redis` (for Redis support)

Usage Example
-------------

In your Django app:

    # Create a signal connection (or use clientsignal.SignalConnection)
    class PingSignalConnection(clientsignal.SignalConnection):
        pass

    # Create Signals
    ping = Signal(providing_args=["ping"])
    pong = Signal(providing_args=["pong"])

    # Register them to broadcast to clients or listen from clients on a
    # SignalConnection 
    PingSignalConnection.listen('ping', ping)
    PingSignalConnection.broadcast('pong', pong)

    # Define a normal Django signal receiver for the remote signal
    @receiver(ping)
    def handle_ping(sender, **kwargs):
        # Send a signal to connected clients
        pong.send(sender=None, pong="Ponged")

In your `settings.py`:

    CLIENTSIGNAL_CONNECTIONS = {
            '/simple': 'myapp.PingSignalConnection',
    }

In your template (jQuery is used here, but not required):

    {% load clientsignal %}
    <!DOCTYPE html>
    <html>
      <head>
        <script src="http://ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js"></script>
        {% clientsignal_js %}
        <script>
          $(function() {
            var sock = new SignalSocket('/simple');

            sock.on('pong', function(data) {
              alert("Pong " + data.pong);
            });

            $('a#ping').click(function(e) { 
              e.preventDefault();
              sock.send('ping', {'ping': 'stringping'});
            });
          });
        </script>
      </head>
      <body>
        <h3><a id="ping" href="">Ping!</a></h3>
      </body>
    </html>


To run (and server Django content too):

    python manage.py runsocket --reload --static --django

Configuration Options
---------------------

### Signal Connections

    CLIENTSIGNAL_CONNECTIONS = {
            '/simple': 'clientsignal.SignalConnection',
    }

This dictionary maps signal connection classes (which should subclass,
at a minimum, `clientsignal.BaseSignalConnection`) to urls that will be
served to socket connections. 

### Backends

Client Signal provides a `RedisSignalConnection` class that allows
cross-process signaling using Redis as a backend. `tornado-redis` is
required.

    CLIENTSIGNAL_BACKEND="[type]://[user]:[password]@[host]:[port]/[db]"
    CLIENTSIGNAL_BACKEND_OPTIONS = {
            'CHANNEL_PREFIX': 'clientsignal',
    }

A URL construction for the backend. For example, a redis server running
on the local host would be addressed as redis://locahost:6379/0. `redis`
is the only type currently supported.

The `CHANNEL_PREFIX` option allows you to prefix all signal connection 
redis channels.

### Object Encoding

JSON limits the kind of objects you can pass as arguments when sending
signals to clients. To assist, Client Signal allows you to declare a
global JSON encoder class and a global JSON object hook:

    CLIENTSIGNAL_JSON_ENCODER='clientsignal.SignalEncoder'
    CLIENTSIGNAL_JSON_OBJECT_HOOK='clientsignal.signal_object_hook'

Unfortunately, these cannot currently be configured on a
per-SignalConnection basis. See the [`simplejson` documentation](http://simplejson.readthedocs.org/en/latest/) for more.

### SockJS

    CLIENTSIGNAL_SOCKJS_URL='http://cdn.sockjs.org/sockjs-0.3.min.js'

Client Signal's `clientsignal_js` template tag will generate a
`<script>` element for SockJS based on this URL. If you do not wish to
use the CDN that is the default, you're free to provide another URL for
the library. If you are using SSL, you'll need to provide an `https://`
URL here.



Commands
--------

The management command `runsocket` takes the following arguments:

- `--reload`: Use code change auto-reloader
- `--django`: Serve the full Django application
- `--static`: Serve static files (requires --django)

Note: `--static` *uses the Django static file handler to serve static files*. 
This may be changed in a future version. 

The ideal deployment of Client Signals would have seperate processes
running for the Django web application and the socket server, using
Redis to broker messages between them (`CLIENTSIGNAL_BACKEND`) and
something like HAProxy on the front end. 

Stats
-----

Client Signal includes an option `clientsignal.stats` app that can
display the live status of signal connections. There are multiple ways
that the stats admin view can be configured. If the 
[`django-adminplus` app](https://github.com/jsocol/django-adminplus)
is present, the "Client Signal Stats" view will appear under custom
views. Otherwise, you may include it in your `urls.py` *before*
`admin.site.urls`:

urlpatterns = patterns('',
    url(r'^admin/clientsignal_stats/$', 'clientsignal.stats.admin.stats_view'),
    url(r'^admin/', include(admin.site.urls)),
)

You will have to navigate to the URL manually, unless you wish to modify
your admin `index.html`.

### Configuration

    INSTALLED_APPS = (
        ...
        'clientsignal.stats',
    )

    CLIENTSIGNAL_STATS = {
            'period': 1000,
            'hosts': [
                'http://localhost:8000',
            ],
            'connections': [
                'clientsignal.SignalConnection',
            ],
            'connectionClass': 'clientsignal.stats.signals.StatsSignalConnection',
    }

`period` is set in miliseconds and determines how frequently the stats
are updated. 

`hosts` is a list of running client signal servers. These are the hosts
whose stats the stats admin view will display.

`connections` is a list of the specific `SignalConnection` subclasses
for which to view stats. Please note: a class that has subclasses will
display those subclasses' connections.

`connectionClass` is the `StatsSignalConnection` class that is used to
send/receive signals from the stats admin view. 

Miscellaneous Features
----------------------

### Authentication

Django Client Signals builds a Django request for each connection that
includes session and authentication information. Presuming a user has
logged in elsewhere in Django (and thus has a valid session id), your
custom SignalConnection class could do the following:

    class MySignalConnection(clientsignal.SignalConnection):

        def on_open(self, connection_info):
            super(MySignalConnection, self).on_open(connection_info)

            # Require authentication
            if self.request.user == AnonymousUser:
                return False


### Caching Middleware

Generally speaking, Client Signals tries to load Django middleware for
each connection. One of the few types of middleware that is relevant is
caching middleware. Client Signal has been tested with Johnny Cache's
query cache middleware, and works. This means you can use the same
memcached (or whatever) query cache for both a Django app served via
some other means (wsgi, etc) and a seperate Client Signals process (or
processes, or processes on multiple servers). 

No additional configuration is necessary for this. Just be sure to call 
your superclass `on_open()` method if you override it.

TODO
----

- Multiplexed `SignalConnection`
- Custom JSON encoding/decoding for each `SignalConnection` class.
- More Django-ish URL handling, perhaps dynamic URLs

From Tornadio2
--------------

Previous versions used Tornadio2 and socket.io. SockJS is more robust,
more stable, and more flexible, and doesn't treat non-node.js servers as
second-class citizens. Most importantly, it's not abandonware like
socket.io appears to be. 

The above code example should provide the necessary starting point to
migrate from previous tornadio2 versions.
