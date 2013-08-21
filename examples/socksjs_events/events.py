
import tornado.ioloop
import tornado.web

from sockjs.tornado import SockJSConnection, SockJSRouter

######

import sockjs
import simplejson

def json_encode(data):
    """ Encode the object with the configuable object hook. """
    return simplejson.dumps(data,
            separators=(',', ':'))

def json_decode(data):
    """ Decode the object with the configuable object hook. """
    return simplejson.loads(data)

# XXX: Monkeypatch these in. I dislike doing this, but there's no other
# means to provide custom json encoding/decoding.
sockjs.tornado.proto.json_encode = json_encode
sockjs.tornado.proto.json_decode = json_decode

# Create an "event", which is basically a message that encapsulates a
# name and some keyword arguments. Presently, only kwargs are used.
def encode_event(name, *args, **kwargs):
    e = {'event':name, 'data':kwargs}
    return json_encode(e);

from inspect import ismethod, getmembers

def on_message_wrapper(original_on_message):
    def new_on_message(self, message):
        try:
            json_message = json_decode(message)
        except simplejson.scanner.JSONDecodeError:
            # Not a json message.
            original_on_message(self, message)
        else:
            # It was a json message. Check to see if it was an event.
            if isinstance(json_message, dict):
                try:
                    e_name = json_message['event']
                    e_kwargs = json_message['data']
                except KeyError:
                    # No event in message, or no event of that name
                    # Call the original on_message.
                    original_on_message(self, message)
                else:
                    self.on_event(e_name, e_kwargs)
            else:
                original_on_message(self, message)

    return new_on_message


# Populate a private list of events for the class based on any methods
# that begin with "event_".
class EventHandlerMeta(type):
    def __init__(cls, name, bases, attrs):
        # Find all events, including bases.
        is_event = lambda m: ismethod(m) and m.__name__.startswith('event_')
        events = [(n[6:], e) for n,e in getmembers(cls, is_event)]

        # Set the _events dictionary for lookup.
        setattr(cls, '_events', dict(events))

        # Wrap the on_message() method of the class to handle events.
        cls.on_message = on_message_wrapper(cls.on_message)

        super(EventHandlerMeta, cls).__init__(name, bases, attrs)


# A base SockJS connection class that includes multiplexing and events.
class EventConnection(SockJSConnection):
    __metaclass__ = EventHandlerMeta

    def on_event(self, name, kwargs=dict()):
        handler = self._events.get(name)
        if handler:
            try:
                return handler(self, **kwargs)
            except TypeError:
                logger.error(('Attempted to call event handler %s ' +
                              'with %s arguments.') % (handler,
                                                       repr(kwargs)))
            raise
        else:
            logger.error('Invalid event name: %s' % name)

    def send_event(self, name, **kwargs):
        event = encode_event(name, **kwargs)
        self.send(event)

    # socket.io nomenclature.
    def emit(self, name, **kwargs):
        return self.send_event(name, **kwargs)

#####

class TestConnection(EventConnection):

    def on_message(self, message):
        print "got message", message

    def on_event(self, name, kwargs):
        super(TestConnection, self).on_event(name, kwargs)

    def event_echo(self, **kwargs):
        print "got echo event", kwargs
        self.send_event("echo", **kwargs)


# Index page handler
class IndexHandler(tornado.web.RequestHandler):
    """Regular HTTP handler to serve the chatroom page"""
    def get(self):
        self.render('events.html')

class EventsJSHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('events.js')

if __name__ == "__main__":
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

    # Create multiplexer
    eventRouter = SockJSRouter(TestConnection, '/events')

    # Create application
    app = tornado.web.Application(
            [(r"/", IndexHandler), (r"/events.js", EventsJSHandler)] + eventRouter.urls
    )
    app.listen(8080)
    tornado.ioloop.IOLoop.instance().start()
