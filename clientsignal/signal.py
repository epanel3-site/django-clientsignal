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

import weakref

import clientsignal.settings as app_settings
from clientsignal.utils import get_signalconnection
from clientsignal.utils import get_class_or_func

import logging
log = logging.getLogger(__name__)


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


