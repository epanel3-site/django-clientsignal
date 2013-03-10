# -*- coding: utf-8 -*-

import tornado

import redis
import tornadoredis
import json

import clientsignal.settings as app_settings
from clientsignal.conn import BaseSignalConnection

from clientsignal.utils import get_class_or_func
from clientsignal.utils import get_backend_url_parts

import logging
log = logging.getLogger(__name__)

# Redis pool
REDIS_URL = get_backend_url_parts(app_settings.CLIENTSIGNAL_BACKEND)
REDIS_CONNECTION_POOL = tornadoredis.ConnectionPool(
        host=REDIS_URL.get('host', 'localhost'),
        port=REDIS_URL.get('port', 'localhost'),
        max_connections=500,
        wait_for_available=True)
REDIS_URL = get_backend_url_parts(app_settings.CLIENTSIGNAL_BACKEND_DEFAULT)

# Redis client for publishing
REDIS = redis.Redis()

class RedisSignalConnection(BaseSignalConnection):
    # The redis channel is this signalconnection's endpoint, therefore
    # redis signal connections must have an endpoint.

    __channel__ = app_settings.CLIENTSIGNAL_BACKEND_OPTIONS.get('CHANNEL_PREFIX', 'clientsignal') + "_default"

    __broadcast_listeners__ = {}

    # This is called from the Django side.
    @classmethod
    def register_signal(cls, name, signal, listen=False, broadcast=False):
        super(RedisSignalConnection, cls).register_signal(name, 
                signal, listen=listen, broadcast=broadcast)

        if listen:
            # Create an event handler to wrap the signal from a client
            # and add it to the SocketConnection's _events.
            # This treats it as if it were an @event
            def handler(conn, *args, **kwargs):
                log.info("LISTEN: Sending signal from client %s(%s)" % (name, kwargs))
                # kwargs['__signal_connection__'] = conn
                signal.send(conn.request.user, **kwargs)

            if name not in cls._events:
                log.info("Registering signal to listen from client %s" % name)
                cls._events[name] = handler

        if broadcast:
            ## Broadcast Signals
            # Generate a listener function for the given signal with the
            # given name and return it. This function will be connected to
            # the signal and will publish it to Redis on receipt.
            def listener_factory(name, signal):
                def listener(sender, **kwargs):
                    # Remove the 'signal' object from the kwargs, it's not
                    # serializable, and we don't need it.
                    del kwargs['signal']
                    kwargs['sender'] = sender

                    json_event = json.dumps({'name':name, 'kwargs':kwargs}, cls=get_class_or_func(app_settings.CLIENTSIGNAL_DEFAULT_ENCODER))
                    log.info("BROADCAST: Sending %s(%s) signal to Redis channel %s" % (name, json_event, cls.__channel__))
                    REDIS.publish(cls.__channel__, json_event)

                return listener

            # Receive the signal within Django and publish it to the Redis
            # channel for this connection.
            if name not in cls.__broadcast_listeners__:
                log.info("Registering signal for broadcast to client %s" % name)

                listener = listener_factory(name, signal)
                cls.__broadcast_listeners__[name] = listener

                # We don't want a weakref to the handler function, we don't
                # want it garbage collected.
                # log.info("BROADCAST: %s Listening for %s" % (cls.__name__, name))
                signal.connect(listener, weak=False)

    def on_open(self, connection_info):
        super(RedisSignalConnection, self).on_open(connection_info)

        # Fire up the redis connection
        self.__channel_listen()
        
    def on_close(self):
        # Since we're using a redis connection pool, disconnect the
        # client on close.
        log.info("CLOSING REDIS SIGNAL CONNECTION ? " + str(self));
        # self.__redis.unsubscribe(self.__channel__)
        # self.__redis.disconnect()

    @tornado.gen.engine
    def __channel_listen(self):
        self.__redis = tornadoredis.Client(
                host=REDIS_URL.get('host', 'localhost'),
                port=REDIS_URL.get('port', 'localhost'),
                # host=REDIS_URL.get('host', 'localhost'),
                # port=REDIS_URL.get('post') or 6379,
                # selected_db=REDIS_URL.get('path'),
                connection_pool=REDIS_CONNECTION_POOL)
        self.__redis.connect()
        yield tornado.gen.Task(self.__redis.subscribe, self.__channel__)
        self.__redis.listen(self.__load_broadcast_event)

    def __load_broadcast_event(self, message):
        # XXX: Effectively, what this does is un-json so we can re-json
        # in a different form. Surely there's a more efficient way.
        if message.kind != 'message':
            return

        # 'message' is a tornadoredis.client.Message
        json_event = message.body

        log.info("Loading Signal from Redis channel %s: %s" %
                (self.__channel__, json_event))

        # Load the event from json and fire of the on_event handler.
        # Every event should have a name and kwargs
        # event_dict = {'name': 'myevent', kwargs':{}}
        event_dict = json.loads(json_event,
                object_hook=get_class_or_func(app_settings.CLIENTSIGNAL_OBJECT_HOOK))

        # If this is a broadcast signal we recognize, send it to the
        # client.
        if event_dict['name'] in self.__broadcast_signals__:
            # If the sender is NOT this connection (i.e. the signal
            # was received over this connection, send it on.
            if event_dict['kwargs']['sender'] != self.request.user:
                log.info("Sending signal loaded from Redis channel: %s %s" % (event_dict['name'], event_dict['kwargs']))
                self.send_signal(event_dict['name'], **event_dict['kwargs'])
            
