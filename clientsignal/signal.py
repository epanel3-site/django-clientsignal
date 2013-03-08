# -*- coding: utf-8 -*-

import weakref

import clientsignal.settings as app_settings
from clientsignal.utils import get_signalconnection
from clientsignal.utils import get_class_or_func

import logging
log = logging.getLogger(__name__)


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
    # log.info("Listening for signal " + name)
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
    # log.info("Broadcasting signal " + name)
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
    # log.info("Registering signal " + name)
    connection.register_signal(name, signal, listen=True, broadcast=True)


