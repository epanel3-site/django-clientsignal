Django Client Signals
=====================

This is an experiment and proof-of-concept at the moment. I really don't 
recommend using it for anything serious. 

Django Client Signals is a SockJS-Tornado-based mechanism for sending
and receiving Django signals as client-side events.

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

    clientsignal.broadcast('pong', pong)
    clientsignal.listen('ping', ping)

    # Define a normal Django signal receiver for the remote signal
    @receiver(ping)
    def handle_ping(sender, **kwargs):
        # Send a signal to connected clients
        pong.send(sender=None, pong="Ponged")

In your settings.py:

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



Requirements
------------

- `sockjs-tornado`
- `tornado-redis` (for Redis support)

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

Commands
--------

The management command `runsocket` takes the following arguments:

- `--reload`: Use code change auto-reloader
- `--django`: Serve the full Django application
- `--static`: Serve static files (requires --django)

Note: `--static` does *not* use Tornado to serve the static files. It
uses the Django static file handler instead. This may be changed in a
future version. 

The ideal deployment of Client Signals would have seperate processes
running for the Django web application and the socket server, using
Redis to broker messages between them (`CLIENTSIGNAL_BACKEND`) and
something like HAProxy on the front end. 

TODO
----

- Multiplexed `SignalConnection`
- Custom JSON encoding/decoding for each `SignalConnection` class.
- More Django-ish URL handling, perhaps dynamic URLs
- Stats

From Tornadio2
--------------

Previous versions used Tornadio2 and socket.io. SockJS is more robust,
more stable, and more flexible, and doesn't treat non-node.js servers as
second-class citizens. Most importantly, it's not abandonware like
socket.io appears to be. 

The above code example should provide the necessary starting point to
migrate from previous tornadio2 versions.
