# -*- coding: utf-8 -*-

import tornado

import redis
import tornadoredis
import json

import clientsignal.settings as app_settings
from clientsignal.conn import BaseSignalConnection, json_event

from clientsignal.utils import get_class_or_func
from clientsignal.utils import get_backend_url_parts

import logging
log = logging.getLogger(__name__)

# Redis pool
REDIS_URL = get_backend_url_parts(app_settings.CLIENTSIGNAL_BACKEND)
# REDIS_CONNECTION_POOL = tornadoredis.ConnectionPool(
#         max_connections=40,
#         wait_for_available=True)

# Redis client for publishing
REDIS = tornadoredis.Client(
                host=REDIS_URL.get('host', 'localhost'),
                port=REDIS_URL.get('port', 6379) or 6379)
REDIS.connect()

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
                log.debug("Registering signal to listen from client %s" % name)
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

                    json_evt = json.dumps({'name':name, 'args':kwargs}, cls=get_class_or_func(app_settings.CLIENTSIGNAL_DEFAULT_ENCODER))
                    log.info("BROADCAST: Encoding and Sending %s(%s) signal to Redis channel %s" % (name, json_evt, cls.__channel__))
                    try:
                        REDIS.publish(cls.__channel__, "%s:%s" % (name, json_evt))
                    except Exception, e:
                        log.error("Cannot publish to redis: %s" % e);

                return listener

            # Receive the signal within Django and publish it to the Redis
            # channel for this connection.
            if name not in cls.__broadcast_listeners__:
                log.debug("Registering signal for broadcast to client %s" % name)

                listener = listener_factory(name, signal)
                cls.__broadcast_listeners__[name] = listener

                # We don't want a weakref to the handler function, we don't
                # want it garbage collected.
                # log.info("BROADCAST: %s Listening for %s" % (cls.__name__, name))
                signal.connect(listener, weak=False)

    def on_open(self, connection_info):
        # Fire up the redis connection
        self.__redis_listen()

        super(RedisSignalConnection, self).on_open(connection_info)
        
    def on_close(self):
        # Since we're using a redis connection pool, disconnect the
        # client on close.
        log.info("CLOSING REDIS SIGNAL CONNECTION ? " + str(self));
        self.__redis.disconnect()

    @tornado.gen.engine
    def __redis_listen(self):
        self.__redis = tornadoredis.Client(
                host=REDIS_URL.get('host', 'localhost'),
                port=REDIS_URL.get('port', 6379) or 6379)
        self.__redis.connect()
        yield tornado.gen.Task(self.__redis.subscribe, self.__channel__)
        self.__redis.listen(self.__on_redis_message)

    def __on_redis_message(self, message):
        # XXX: Effectively, what this does is un-json so we can re-json
        # in a different form. Surely there's a more efficient way.
        if message.kind != 'message':
            return

        # log.info("Loading JSON Signal from Redis channel %s: %s" %
        #         (self.__channel__, message.body))

        # 'message' is a tornadoredis.client.Message
        name, json_evt = message.body.split(':', 1)

        if name in self.__broadcast_signals__:
            log.info("Sending JSON signal from Redis: %s %s %s" % (self, name, json_evt))
            msg = json_event(self.endpoint, name, None, json_evt)
            self.session.send_message(msg)

