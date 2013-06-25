# -*- coding: utf-8 -*-

import tornadio2
import json

from django.conf import settings
from django.utils.importlib import import_module

from django.dispatch import Signal, receiver
from django.utils.importlib import import_module
from django import http
from django.contrib.auth import get_user
from django.contrib.auth.models import User, AnonymousUser

import clientsignal.settings as app_settings
from clientsignal.utils import get_signalconnection
from clientsignal.utils import get_class_or_func

import logging
log = logging.getLogger(__name__)


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

def json_event(endpoint, name, message_id, json_evt):
    """ Generate an event message based on already json'ed arguments. """

    return u'5:%s:%s:%s' % (
        message_id or '',
        endpoint or '',
        json_evt
    )
    

# XXX: Monkeypatch this back in. I dislike doing this.
tornadio2.conn.event = event

def json_load(msg):
    """ Load json-encoded object with the configuable object hook. """
    return json.loads(msg,
            object_hook=get_class_or_func(app_settings.CLIENTSIGNAL_OBJECT_HOOK))

# XXX: Monkeypatch this back in. I dislike doing this.
tornadio2.proto.json_load = json_load

class SignalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BaseSignalConnection):
            d = {'user': obj.request.user.username}
            return d

        if isinstance(obj, AnonymousUser):
            return {}

        if isinstance(obj, User):
            d = {'username': obj.username}
            return d

        if isinstance(obj, http.HttpRequest):
            return {}

        return json.JSONEncoder.default(self, obj)


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


class DjangoRequestSocketConnection(tornadio2.SocketConnection):
    """ 
    TornadIO2 SocketConnection that builds a Django request on open.
    This effectively handles authentication.
    """

    def __init__(self, session, endpoint=None):
        super(DjangoRequestSocketConnection, self).__init__(session, endpoint=endpoint)
        self.load_middleware()

    def __str__(self):
        try:
            return "<%s %s %s %s>" % (self.__class__.__name__,
                    self.endpoint, self.request.user, id(self))
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

class BaseSignalConnection(DjangoRequestSocketConnection):

    # When register() is called for a specific connection, the signals
    # being registered are stored here.
    __listen_signals__ = {}
    __broadcast_signals__ = {}
    
    @classmethod
    def register_signal(cls, name, signal, listen=False, broadcast=False):
        """ 
        Register the signal. The signal can either be listened for by
        this connection, broadcast by this connection (if it is sent),
        or both. 

        Signals that are listened for from the client are wrapped
        similarly to TornadIO2's @event()s. 
        """
        if listen and name not in cls.__listen_signals__:
            cls.__listen_signals__[name] = signal

        if broadcast and name not in cls.__broadcast_signals__:
            cls.__broadcast_signals__[name] = signal
            
    def send_signal(self, name, **kwargs):
        """ 
        Send a signal to the client with the given names and the given 
        kwargs. This function simply wraps the tornadio2.SocketConnection 
        emit() function for possible overrides. 
        """
        log.debug("Sending signal named " + name)
        self.emit(name, **kwargs)

    def emit(self, name, *args, **kwargs):
        """ 
        Send socket.io event. This overrides the SocketConnection emit()
        to provide for optional encoders.
        """
        if self.is_closed:
            return

        msg = event(self.endpoint, name, None, *args, **kwargs)
        self.session.send_message(msg)

    
class SimpleSignalConnection(BaseSignalConnection):

    @classmethod
    def register_signal(cls, name, signal, listen=False, broadcast=False):
        super(SimpleSignalConnection, cls).register_signal(name, 
                signal, listen=listen, broadcast=broadcast)

        if listen:
            # Create an event handler to wrap the signal and add it to
            # the SocketConnection's _events.
            def handler(conn, *args, **kwargs):
                log.info(str(conn) + " received signal " + name)
                
                # kwargs['__signal_connection__'] = conn
                signal.send(conn.request.user, **kwargs)

            cls._events[name] = handler

    
    def on_open(self, connection_info):
        super(SimpleSignalConnection, self).on_open(connection_info)

        # Generate a listener function for the given signal with the
        # given name and return it. That function will handle "emitting"
        # the signal as a socket.io event on this connection.
        def listener_factory(name, signal):
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
            listener = listener_factory(name, signal)
            # We don't want a weakref to the handler function, we don't
            # want it garbage collected.
            signal.connect(listener, weak=False)

    def on_event(self, name, args=[], kwargs=dict()):
        """ Receive socket.io events and send Django Signals. """

        self.event_signal.send(sender=self, event=name, request=self.request, **kwargs)
        return super(SignalConnection, self).on_event(name, args, kwargs)

