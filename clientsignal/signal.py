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

import tornadio2
import json

from django.dispatch import Signal, receiver
from django.utils.importlib import import_module
from django import http
from django.contrib.auth import get_user
from django.contrib.auth.models import User

import clientsignal.settings as app_settings
from clientsignal.utils import get_signalconnection
from clientsignal.utils import get_class_or_func

import logging
log = logging.getLogger(__name__)

# Some signals to respond to client-side events
client_connected = Signal(providing_args=['request'])
client_disconnected = Signal(providing_args=['request'])
client_message = Signal(providing_args=['request', 'message'])
client_event = Signal(providing_args=['request', 'event'])

@receiver(client_connected)
def handle_connection(sender, request, **kwargs):
    log.info("Connected: " + str(sender))

@receiver(client_disconnected)
def handle_disconnection(sender, request, **kwargs):
    log.info("Disconnected: " + str(sender))

@receiver(client_message)
def handle_message(sender, message, **kwargs):
    log.info("Message: " + str(sender) + " " + message)

@receiver(client_event)
def handle_event(sender, event, **kwargs):
    log.info("Event: " + str(sender) + " " + event)


def build_request(connection_info, path = None):
    from django.contrib.sessions.backends.db import SessionStore
    
    request = http.HttpRequest()
    request.path = path
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


def event(endpoint, name, message_id, *args, **kwargs):
    """ Generate event message. This function is based on the TornadIO2
    proto.event() function with the added option of a simplejson
    encoder. """
    if args:
        evt = dict(
            name=name,
            args=args
            )

        if kwargs:
            log.error('Can not generate event() with args and kwargs.')
    else:
        evt = dict(
            name=name,
            args=[kwargs]
        )

    return u'5:%s:%s:%s' % (
        message_id or '',
        endpoint or '',
        json.dumps(evt,
            cls=get_class_or_func(app_settings.CLIENTSIGNAL_DEFAULT_ENCODER))
    )

def json_load(msg):
    """ Load json-encoded object with the configuable object hook. """
    return json.loads(msg,
            object_hook=get_class_or_func(app_settings.CLIENTSIGNAL_OBJECT_HOOK))

# XXX: Monkeypatch this back in. I dislike doing this.
tornadio2.proto.json_load = json_load


class SignalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, SignalConnection):
            d = {'user': obj.request.user.username}
            return d

        if isinstance(obj, User):
            d = {'username': obj.username}
            return d

        if isinstance(obj, http.HttpRequest):
            return {}

        return json.JSONEncoder.default(self, obj)


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
    __listen_signals__ = {}
    __broadcast_signals__ = {}

    def __str__(self):
        return "%s SignalConnection" % self.request.user

    @classmethod
    def register_signal(cls, name, signal, listen=False, broadcast=False):
        """ 
        Register the signal. The signal can either be listened for by
        this connection, broadcast by this connection (if it is sent),
        or both. 

        Signals that are listened for from the client are wrapped
        similarly to TornadIO2's @event()s. 
        """
        if listen:
            cls.__listen_signals__[name] = signal

            # Create an event handler to wrap the signal and add it to
            # the SocketConnection's _events.
            def handler(conn, *args, **kwargs):
                log.info("Sending signal " + name)
                signal.send(conn.request.user, **kwargs)

            cls._events[name] = handler

        if broadcast:
            cls.__broadcast_signals__[name] = signal

    def send_signal(self, name, **kwargs):
        """ 
        Send a signal to the client with the given names and the given 
        kwargs. This function simply wraps the tornadio2.SocketConnection 
        emit() function for possible overrides. 
        """
        log.info("Sending signal named " + name)
        self.emit(name, **kwargs)

    def on_open(self, connection_info):
        self.request = build_request(connection_info)
        self.connected_signal.send(sender=self, request=self.request)

        log.info("Opened " + str(self))
        # log.info("Listening: " + str(self.__listen_signals__))
        # log.info("Events: " + str(self._events))
        # log.info("Broadcasting: " + str(self.__broadcast_signals__))

        # Generate a listener function for the given signal with the
        # given name and return it. That function will handle "emitting"
        # the signal as a socket.io event on this connection.
        def listener_function(name, signal):
            def listener(sender, **kwargs):
                # Remove the 'signal' object from the kwargs, it's not
                # serializable, and we don't need it.
                del kwargs['signal']
                kwargs['sender'] = sender

                # If the sender is NOT this connection (i.e. the signal
                # was received over this connection, send it on.
                if sender != self:
                    log.info(str(self) + " sending signal " + name)
                    self.send_signal(name, **kwargs)
            
            return listener

        # Receive the signal within Django and send it to the client as a
        # socket.io event.
        for name, signal in self.__broadcast_signals__.items():
            listener = listener_function(name, signal)
            # We don't want a weakref to the handler function, we don't
            # want it garbage collected.
            signal.connect(listener, weak=False)

        
    def on_close(self):
        self.disconnected_signal.send(sender=self, request=self.request)


    def on_message(self, message):
        self.message_signal.send(sender=self, request=self.request, message=message)


    def on_event(self, name, args=[], kwargs=dict()):
        """ Receive socket.io events and send Django Signals. """

        self.event_signal.send(sender=self, event=name, request=self.request, **kwargs)
        return super(SignalConnection, self).on_event(name, args, kwargs)

    def emit(self, name, *args, **kwargs):
        """ 
        Send socket.io event. This overrides the SocketConnection emit()
        to provide for optional encoders.
        """
        if self.is_closed:
            return

        msg = event(self.endpoint, name, None, *args, **kwargs)
        self.session.send_message(msg)


def listen(name, signal, connection=None):
    """ Register the given signal with the given name to be recieved
    from client senders. """
    
    if not connection:
        # Use the top-level multiplexed connection class if we're not
        # given one.
        connection = get_signalconnection(
                app_settings.CLIENTSIGNAL_MULTIPLEXED_CONNECTION)

    # Register the signal with the connection so that client socket.io
    # events with the given name are sent as signals within Django when
    # received.
    log.info("Listening for signal " + name)
    connection.register_signal(name, signal, listen=True)


def broadcast(name, signal, connection=None):
    """ Register the given signal with the given name to be sent to
    client receivers. """
    
    if not connection:
        # Use the top-level multiplexed connection class if we're not
        # given one.
        connection = get_signalconnection(
                app_settings.CLIENTSIGNAL_MULTIPLEXED_CONNECTION)
    

    # Register the signal with the connection so that client socket.io
    # events with the given name are sent as signals within Django when
    # received.
    log.info("Broadcasting signal " + name)
    connection.register_signal(name, signal, broadcast=True)
    

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
    log.info("Registering signal " + name)
    connection.register_signal(name, signal, listen=True, broadcast=True)


