# -*- coding: utf-8 -*-
#
# Copyright 2012 Will Barton. 
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

## Backend settings: 

# Right now a redis backend is the only kind supported. 

# "redis://:password@host:port/db"
CLIENTSIGNAL_BACKEND_DEFAULT = ''
CLIENTSIGNAL_BACKEND = getattr(settings, 
        'CLIENTSIGNAL_BACKEND',
        CLIENTSIGNAL_BACKEND_DEFAULT)

CLIENTSIGNAL_BACKEND_OPTIONS_DEFAULT = {
        'CHANNEL_PREFIX': 'clientsignal',
}
CLIENTSIGNAL_BACKEND_OPTIONS = getattr(settings, 
        'CLIENTSIGNAL_BACKEND_OPTIONS',
        CLIENTSIGNAL_BACKEND_OPTIONS_DEFAULT)

# XXX: SockJS doesn't support multiplexing out of the box. It's
# something we'll have to add back at some point in the future.
#
# CLIENTSIGNAL_MULTIPLEXED_CONNECTION_DEFAULT = 'clientsignal.SignalConnection'
# CLIENTSIGNAL_BASE_SIGNALCONNECTION_DEFAULT = 'clientsignal.SignalConnection'
#
# CLIENTSIGNAL_MULTIPLEXED_CONNECTION = getattr(settings, 
#         'CLIENTSIGNAL_MULTIPLEXED_CONNECTION',
#         CLIENTSIGNAL_MULTIPLEXED_CONNECTION_DEFAULT)
# CLIENTSIGNAL_BASE_SIGNALCONNECTION = getattr(settings, 
#         'CLIENTSIGNAL_BASE_SIGNALCONNECTION',
#         CLIENTSIGNAL_BASE_SIGNALCONNECTION_DEFAULT)

## Socket Connection settings

# List of connections and their URLs
# Ex:
#   CLIENTSIGNAL_CONNECTIONS = {
#           '/appone_signals': appone.AppOneSignalConnection,
#           '/apptwo_signals': apptwo.AppTwoSignalConnection,
#   }
CLIENTSIGNAL_CONNECTIONS_DEFAULT = {}
CLIENTSIGNAL_CONNECTIONS = getattr(settings, 
        'CLIENTSIGNAL_CONNECTIONS',
        CLIENTSIGNAL_CONNECTIONS_DEFAULT)


## Custom JSON Encoding Settings
CLIENTSIGNAL_JSON_ENCODER_DEFAULT = 'clientsignal.SignalEncoder'
CLIENTSIGNAL_JSON_ENCODER = getattr(settings, 
        'CLIENTSIGNAL_JSON_OBJECT_HOOK',
        CLIENTSIGNAL_JSON_ENCODER_DEFAULT)
CLIENTSIGNAL_JSON_OBJECT_HOOK_DEFAULT = 'clientsignal.signal_object_hook'
CLIENTSIGNAL_JSON_OBJECT_HOOK = getattr(settings, 
        'CLIENTSIGNAL_JSON_OBJECT_HOOK',
        CLIENTSIGNAL_JSON_OBJECT_HOOK_DEFAULT)

## Socket protocol settings
# CLIENTSIGNAL_PROTOCOLS_DEFAULT = (
#         'websocket',
#         'flashsocket',
#         'xhr-polling',
#         'htmlfile',
#         'jsonp-polling',
# )
# CLIENTSIGNAL_PROTOCOLS = getattr(settings, 
#         'CLIENTSIGNAL_PROTOCOLS',
#         CLIENTSIGNAL_PROTOCOLS_DEFAULT)
# 
# CLIENTSIGNAL_FLASH_POLICY_PORT_DEFAULT = 10843
# CLIENTSIGNAL_FLASH_POLICY_PORT = getattr(settings, 
#         'CLIENTSIGNAL_FLASH_POLICY_PORT',
#         CLIENTSIGNAL_FLASH_POLICY_PORT_DEFAULT)

