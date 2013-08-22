# -*- coding: utf-8 -*-
#
# Copyright 2013 Will Barton. 
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

import clientsignal.settings as app_settings

import sockjs.tornado
import simplejson as json 
# import json

from inspect import ismethod, getmembers

from clientsignal.utils import get_class_or_func

import logging
log = logging.getLogger(__name__)

# First we need to override the json_endcode and json_decode functions
# that sockjs-tornado uses to 

def json_encode(data):
    """ Encode the object with the configuable object hook. """
    encoder_cls = get_class_or_func(app_settings.CLIENTSIGNAL_JSON_ENCODER)
    return json.dumps(data, separators=(',', ':'), cls=encoder_cls)

def json_decode(data):
    """ Decode the object with the configuable object hook. """
    object_hook = get_class_or_func(app_settings.CLIENTSIGNAL_JSON_OBJECT_HOOK)
    return json.loads(data, object_hook=object_hook)


# XXX: Monkeypatch these in. I dislike doing this, but there's no other
# means to provide custom json encoding/decoding.
sockjs.tornado.proto.json_encode = json_encode
sockjs.tornado.proto.json_decode = json_decode


# Create an "event", which is basically a message that encapsulates a
# name and some keyword arguments. Presently, only kwargs are used.
def encode_event(name, **kwargs):
    e = {'event':name, 'data':kwargs}
    return json_encode(e);


# An exception specially for events
class EventException(Exception):
    pass


# Populate a private list of events for the class based on any methods
# that begin with "event_".
class EventHandlerMeta(type):
    def __init__(cls, name, bases, attrs):
        # Find all events, including bases.
        is_event = lambda m: ismethod(m) and m.__name__.startswith('event_')
        events = [(n[6:], e) for n,e in getmembers(cls, is_event)]

        # Set the _events dictionary for lookup.
        setattr(cls, '_events', dict(events))

        super(EventHandlerMeta, cls).__init__(name, bases, attrs)


# A base SockJS connection class that includes multiplexing and events.
# This connection class can only send/receive events. It doesn't send
# plain "messages," and overriding the on_message method in a subclass
# will break events.
class EventConnection(sockjs.tornado.SockJSConnection):
    __metaclass__ = EventHandlerMeta

    def on_message(self, message):
        try:
            json_message = json_decode(message)
        except json.scanner.JSONDecodeError:
            # Not a json message.
            log.error('Invalid event name: %s' % name)
            # raise EventException("message did not contain event")
        else:
            # It was a json message. Check to see if it was an event.
            if isinstance(json_message, dict):
                try:
                    e_name = json_message['event']
                    e_kwargs = json_message['data']
                except KeyError:
                    # No event in message, or no event of that name
                    raise EventException("message did not contain event")
                else:
                    self.on_event(e_name, e_kwargs)
            else:
                log.error('Invalid event name: %s' % name)
                # raise EventException("message did not contain event")

    def on_event(self, name, kwargs=dict()):
        handler = self._events.get(name)
        if handler:
            try:
                return handler(self, **kwargs)
            except TypeError:
                log.error(('Attempted to call event handler %s ' +
                              'with %s arguments.') % (handler,
                                                       repr(kwargs)))
                raise
        else:
            log.error('Invalid event name: %s' % name)
            # raise EventException("no handler for event %s" % name)

    def send(self, name, **kwargs):
        log.info("sending signal %s(%s)" % (name, unicode(kwargs)));
        event = encode_event(name, **kwargs)
        super(EventConnection, self).send(event)

    def send_raw(self, raw_data):
        super(EventConnection, self).send(raw_data)

    # socket.io nomenclature?
    def emit(self, name, **kwargs):
        return self.send(name, **kwargs)

        



