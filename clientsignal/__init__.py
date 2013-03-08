# -*- coding: utf-8 -*-

from clientsignal.signal import register, listen, broadcast
from clientsignal.conn import BaseSignalConnection
from clientsignal.conn import SimpleSignalConnection
from clientsignal.redisconn import RedisSignalConnection

from clientsignal.conn import SignalEncoder

import clientsignal.settings as app_settings

if app_settings.CLIENTSIGNAL_BACKEND.startswith('redis'):
    SignalConnection = RedisSignalConnection
else:
    SignalConnection = SimpleSignalConnection

__all__ = [
            'register', 
            'listen',
            'broadcast',
            'SignalEncoder',
            'BaseSignalConnection',
            'SimpleSignalConnection',
            'RedisSignalConnection',
            'SignalConnection',
          ]

