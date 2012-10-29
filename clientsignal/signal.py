# -*- coding: utf-8 -*-
"""

Django Client Signals

A transparent translation of Django signals into socket.io events using
TornadIO2. 

    # Create Signals
    ping = Signal(providing_args=["ping"])
    pong = Signal(providing_args=["pong"])

    # Register them as client send/receivable
    clientsignal.register('pong', pong)
    clientsignal.register('ping', ping)

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

"""

import weakref
import logging

import tornadio2

from django.dispatch import Signal, receiver
from django.utils.importlib import import_module
from django import http
from django.contrib.auth import get_user

import clientsignal.settings as app_settings
from clientsignal.utils import get_signalconnection

# First, some basic signals to respond to client-side events
client_connected = Signal(providing_args=['request'])
client_disconnected = Signal(providing_args=['request'])
client_message = Signal(providing_args=['request', 'message'])
client_event = Signal(providing_args=['request', 'event'])

@receiver(client_connected)
def handle_connection(sender, request, **kwargs):
    logging.debug("Connected: " + str(sender))

@receiver(client_disconnected)
def handle_disconnection(sender, request, **kwargs):
    logging.debug("Disconnected: " + str(sender))

@receiver(client_message)
def handle_message(sender, message, **kwargs):
    logging.debug("Message: " + str(sender) + " " + message)

@receiver(client_event)
def handle_event(sender, event, **kwargs):
    logging.debug("Event: " + str(sender) + " " + event)


def build_request(connection_info):
    from django.contrib.sessions.backends.db import SessionStore
    
    request = http.HttpRequest()
    # request.path = 
    # request.path_info =
    request.method = 'GET'
    request.GET = connection_info.arguments
    request.COOKIES = http.parse_cookie(connection_info.cookies)
    request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

    # Authentication
    sessionid = request.COOKIES.get('sessionid')
    request.session = SessionStore(session_key=sessionid)
    request.user = get_user(request)

    return request


class SignalConnection(tornadio2.SocketConnection):
    """
    TornadIO2 connection that translates from socket.io to Django
    signals.
    """

    # In case we want to subclass this connection for a specific endpoint.
    connected_signal = client_connected
    disconnected_signal = client_disconnected
    message_signal = client_message
    event_signal = client_event 

    # When register() is called for a specific connection, the signals
    # being registered are stored here.
    __registered_signals__ = {}

    def __str__(self):
        return "%s SignalConnection" % self.request.user

    @classmethod
    def register_signal(cls, name, signal):
        cls.__registered_signals__[name] = signal

    def on_open(self, connection_info):
        self.request = build_request(connection_info)
        self.connected_signal.send(sender=self, request=self.request)

        # Generate a listener function for the given signal with the
        # given name and return it. That function will handle "emitting"
        # the signal as a socket.io event on this connection.
        def listener_function(name, signal):
            def listener(sender, **kwargs):
                # Remove the 'signal' object from the kwargs, it's not
                # serializable, and we don't need it.
                del kwargs['signal']

                # If the sender is NOT this connection (i.e. the signal
                # was received over this connection, send it on.
                if sender != self:
                    self.emit(name, **kwargs)
            
            return listener

        # Set up this connection to listen and send registered signals 
        # Receive the signal within Django and send it to the client as a
        # socket.io event.
        for name, signal in self.__registered_signals__.items():
            listener = listener_function(name, signal)
            # We don't want a weakref to the handler function, we don't
            # want it garbage collected.
            signal.connect(listener, weak=False)

        
    def on_close(self):
        self.disconnected_signal.send(sender=self, request=self.request)


    def on_message(self, message):
        self.message_signal.send(sender=self, request=self.request, message=message)


    def on_event(self, name, *args, **kwargs):
        """ Receive socket.io events and send Django Signals. """

        self.event_signal.send(sender=self, event=name, request=self.request, **kwargs)
        # Lookup a specific signal by the event name to see if we can
        # fire off something a little more specific.
        for n, signal in self.__registered_signals__.items():
            if n == name:
                signal.send(self, **kwargs)


def register(name, signal, connection=None):
    """
    Register the given signal with the given name for client senders and
    receivers.
    """
    
    if not connection:
        # Use the top-level multiplexed connection class if we're not
        # given one.
        connection = get_signalconnection(
                app_settings.CLIENTSIGNAL_MULTIPLEXED_CONNECTION)

    # Register the signal with the connection so that client socket.io
    # events with the given name are sent as signals within Django when
    # received.
    connection.register_signal(name, signal)

