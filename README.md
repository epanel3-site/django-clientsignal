Django Client Signals
=====================

This is an experiment and proof-of-concept at the moment. I really don't recommend using it for anything serious.

TornadIO2-based mechanism for sending and receiving Django signals as 
socket.io client-side events:

    # Create Signals
    ping = Signal(providing_args=["ping"])
    pong = Signal(providing_args=["pong"])

    # Register them to broadcast to clients or listen to clients
    clientsignal.broadcast('pong', pong)
    clientsignal.listen('ping', ping)

    # Define a normal Django signal receiver for the remote signal
    @receiver(ping)
    def handle_ping(sender, **kwargs):
        # Send a signal to connected clients
        pong.send(sender=None, pong="Ponged")

The corrosponding Javascript would be:

    var sock = new io.connect('http://' + window.location.host);

    sock.on('disconnect', function() {
        sock.socket.reconnect();
    });

    sock.on('pong', function(data) {
        alert("Pong " + data.pong)
    });

    $('a#ping').click(function(e) {  
        e.preventDefault();
        sock.emit('ping', {'ping': 'stringping'});
    });

Support is included for TornadIO2/socket.io endpoints.

Requirements
------------

* tornadio2
* tornado-redis (for Redis support)

