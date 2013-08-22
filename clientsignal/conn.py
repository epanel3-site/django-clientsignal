# -*- coding: utf-8 -*-
#
# Copyright 2012-2013 Will Barton. 
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without 
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright 
#      notice, this list of conditions and the following disclaimer.
#   2. Redistributions in binary form must reproduce the above copyright 
#      notice, this list of conditions and the following disclaimer in the 
#      documentation and/or other materials provided with the distribution.
#   3. The name of the author may not be used to endorse or promote products
#      derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL
# THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from django.conf import settings
from django.utils.importlib import import_module

from django.dispatch import Signal, receiver
from django.utils.importlib import import_module
from django import http
from django.contrib.auth import get_user
from django.contrib.auth.models import User, AnonymousUser

import clientsignal.settings as app_settings
from clientsignal.utils import get_class_or_func

from clientsignal.socket import EventConnection, EventHandlerMeta

import logging
log = logging.getLogger(__name__)

# Build a Django Request from the base connection info we received. This
# should handle authentication for us through Django
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


class DjangoRequestConnection(EventConnection):
    """ 
    Connection that builds a Django request on open, allowing Django to
    handle authentication
    """

    def __init__(self, *args, **kwargs):
        super(DjangoRequestConnection, self).__init__(*args, **kwargs)
        self.load_middleware()

    def __str__(self):
        try:
            return "<%s %s %s>" % (self.__class__.__name__,
                    self.request.user, id(self))
        except AttributeError:
            return "<%s %s %s>" % (self.__class__.__name__,
                    self.endpoint, id(self))

    def load_middleware(self):
        """ Based on Django BaseHandler """
        log.debug("Loading middleware")
        for middleware_path in settings.MIDDLEWARE_CLASSES:
            try:
                mw_module, mw_classname = middleware_path.rsplit('.', 1)
            except ValueError:
                raise exceptions.ImproperlyConfigured('%s isn\'t a middleware module' % middleware_path)
            try:
                mod = import_module(mw_module)
            except ImportError, e:
                raise exceptions.ImproperlyConfigured('Error importing middleware %s: "%s"' % (mw_module, e))
            try:
                mw_class = getattr(mod, mw_classname)
            except AttributeError:
                raise exceptions.ImproperlyConfigured('Middleware module "%s" does not define a "%s" class' % (mw_module, mw_classname))
            try:
                mw_instance = mw_class()
            except exceptions.MiddlewareNotUsed:
                continue

            # We're not going to do anything else for now... 

    def on_open(self, connection_info):
        self.request = build_request(connection_info)
        log.info("Opened " + str(self))
           
    def on_close(self):
        log.info("Closed " + str(self))


class SignalHandlerMeta(EventHandlerMeta):
    def __init__(cls, name, bases, attrs):
        # Set the _events dictionary for lookup.
        setattr(cls, '_broadcast_signals', dict())
        setattr(cls, '_listen_signals', dict())
        super(SignalHandlerMeta, cls).__init__(name, bases, attrs)


class BaseSignalConnection(DjangoRequestConnection):
    """
    This is the base level signal connection. It handles registration of
    broadcast and listen signals and provides a stub for sending signals
    that can be overriden by subclasses (provided they call super()).

    Listen Signals:     Signals sent from client -> server
    Broadcast Signals:  Signals sent from server -> clients
    """
    __metaclass__ = SignalHandlerMeta

    @classmethod
    def listen(cls, name, signal):
        """ Register the given signal with the given name to be recieved
        from client senders. """
        
        # Register the signal with the connection so that client events
        # with the given name are sent as the given signal within Django
        # when received.
        # log.info("Listening for signal " + name)
        cls.register_signal(name, signal, listen=True)

    @classmethod
    def broadcast(cls, name, signal):
        """ Register the given signal with the given name to be sent to
        client receivers. """
        
        # Register the signal with the connection so that the given
        # Django signal is sent to the client as an event with the given
        # name when received.
        # log.info("Broadcasting signal " + name)
        cls.register_signal(name, signal, broadcast=True)

    @classmethod
    def register(cls, name, signal):
        """
        Register the given signal with the given name for client senders and
        receivers.
        """
        # Register the signal with the connection so that client events
        # with the given name are sent as signals within Django when
        # received.
        # log.info("Registering signal " + name + " for class " + unicode(cls))
        cls.register_signal(name, signal, listen=True, broadcast=True)

    @classmethod
    def register_signal(cls, name, signal, listen=False, broadcast=False):
        """ 
        Register the signal. The signal can either be listened for by
        this connection, broadcast by this connection (if it is sent),
        or both. 

        Signals that are listened for from the client are wrapped
        as EventConnection events.
        """
        if listen and name not in cls._listen_signals:
            cls._listen_signals[name] = signal

        if broadcast and name not in cls._broadcast_signals:
            cls._broadcast_signals[name] = signal

    def send_signal(self, name, **kwargs):
        """ 
        Send a signal to the client with the given names and the given 
        kwargs. This function simply wraps the EventConnection send()
        method.
        """
        log.debug("Sending signal named " + name)
        self.send(name, **kwargs)

    
class SimpleSignalConnection(BaseSignalConnection):

    _listeners = {}

    @classmethod
    def register_signal(cls, name, signal, listen=False, broadcast=False):
        super(SimpleSignalConnection, cls).register_signal(name, 
                signal, listen=listen, broadcast=broadcast)

        if listen:
            # Create an event handler to wrap the signal and add it to
            # the SocketConnection's _events.
            def handler(conn, *args, **kwargs):
                log.info(str(conn) + " received signal " + name)
                signal.send(conn.request.user, **kwargs)

            cls._events[name] = handler
    
    def on_open(self, connection_info):
        super(SimpleSignalConnection, self).on_open(connection_info)

        # Generate a listener function for the given signal with the
        # given name and return it. That function will handle sending 
        # the signal as an event on this connection.
        def listener_factory(name, signal):
            def listener(sender, **kwargs):
                # Remove the 'signal' object from the kwargs, it's not
                # serializable, and we don't need it.
                del kwargs['signal']
                kwargs['sender'] = sender

                # If the sender is NOT this connection (i.e. the signal
                # was received over this connection or send it on.
                if sender != self:
                    self.send_signal(name, **kwargs)
            
            return listener

        # Receive the signal within Django and send it to the client as a
        # event.
        for name, signal in self._broadcast_signals.items():
            listener = listener_factory(name, signal)
            self._listeners[name] = listener
            # We don't want a weakref to the handler function, we don't
            # want it garbage collected.
            signal.connect(listener, weak=False)

    def on_close(self):
        # Disconnect signals that this connection was listening to.
        for name, signal in self._broadcast_signals.items():
            listener = self._listeners[name]
            signal.disconnect(listener, weak=False)

        super(SimpleSignalConnection, self).on_close();

