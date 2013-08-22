from django.dispatch import Signal, receiver

import clientsignal

import logging
log = logging.getLogger(__name__)

# Create Signals
ping = Signal(providing_args=["ping"])
pong = Signal(providing_args=["pong"])

# Register them as client send/receivable
clientsignal.SimpleSignalConnection.listen('ping', ping)
clientsignal.SimpleSignalConnection.broadcast('pong', pong)

# Define a normal Django signal receiver for the remote signal
@receiver(ping)
def handle_ping(sender, **kwargs):
    # Send a signal to connected clients
    log.info("Got a ping signal from %s" % unicode(sender))
    pong.send(sender="ME", pong="Ponged")
    log.info("sent pong")

@receiver(pong)
def handle_pong(sender, **kwargs):
    log.info("Got a pong");

