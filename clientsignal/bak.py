

class ClientSignal(Signal):
    """
    Push a signal out to a client with given arguments.

    This signal is meant to be mostly API-compatible with Django
    signals, except that all signal instances have an internal name.
    There is a comparable Javascript API for client-side signals.
    """

    def __init__(self, name, providing_args=None,
            serializer=None, deserializer=None):
        """
        Create a new signal.

        name
            The name that clients will use to register for this signal.

        providing_args
            A list of the arguments this signal can pass along in a send() call.

        serializer
            A function to serialize the provided arguments 
        """
        self.name = name

        self.serializer = serializer
        if self.serializer is None:
            self.serializer = settings.CLIENTSIGNAL_SERIALIZER

        self.deserializer = deserializer
        if self.deserializer is None:
            self.deserializer = settings.CLIENTSIGNAL_DESERIALIZER

        return super(ClientSignal, self).__init__(providing_args=providing_args)


    def connect(self, receiver, sender=None, weak=True, dispatch_uid=None):
        super(ClientSignal, self).connect(
                receiver, sender=sender, weak=weak, dispatch_uid=dispatch_uid)


    def disconnect(self, receiver=None, sender=None, weak=True, dispatch_uid=None):
        super(ClientSignal, self).disconnect(
                receiver=receiver, sender=sender, weak=weak, dispatch_uid=dispatch_uid)


    def send(self, sender, **named):
        """
        Send signal to the transport service from sender to all connected receivers.

        No response is returned, unlike normal Django signals. If
        'model' is given in the arguments and 'id' is not, the model 

        Arguments:

            sender
                The sender of the signal Either a specific object or None.

            named
                Named arguments which will be passed to receivers.

        """

        responses = []
        if not self.receivers:
            return responses

        for receiver in self._live_receivers(_make_id(sender)):
            response = receiver(signal=self, sender=sender, **named)
            responses.append((receiver, response))
        return responses


    def __send(self, sender, **named):
        params = {
                '__signal__': self.__class__,
                '__signal_arguments__': self.serializer(sender, **named),
                }

        # Call the transport via http request
        # The transport will ALWAYS run on localhost.
        try:
            urllib.urlopen(
                    'http://localhost:%d/notify' % settings.SIGNALPUSH_NOTIFIER_PORT,
                    urllib.urlencode(params))
            return True
        except IOError:
            return False

        return response


    def receive(self, **params):
        """
        Recieve the signal sent by a Django application.

        This is a class method, and mostly internal. 
        """

        signal_name = params['__signal__']
        signal_arguments = params['__signal_arguments__']

        

        responses = []
        if not self.receivers:
            return responses

        for receiver in self._live_receivers(_make_id(sender)):
            response = receiver(signal=self, sender=sender, **named)
            responses.append((receiver, response))

        return responses

    def send_robust(self, sender, **named):
        return self.send(sender, **named)


def default_serializer(sender, **kwargs):
    kwargs['__sender_instance__'] = sender.id
    kwargs['__sender_model__'] = sender.__class__
 
    json = simplejson.dumps(kwargs)
   
    return json

def default_deserializer(*args, **kwargs):
    # kwargs['__sender_instance__'] = sender.id
    # kwargs['__sender_model__'] = sender.__class__
 
    json = simplejson.dumps({'args':args, 'kwargs':kwargs})
   
    return json
            
