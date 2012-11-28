# -*- coding: utf-8 -*-

from django.conf import settings

CLIENTSIGNAL_MULTIPLEXED_CONNECTION_DEFAULT = 'clientsignal.SignalConnection'
CLIENTSIGNAL_BASE_SIGNALCONNECTION_DEFAULT = 'clientsignal.SignalConnection'

CLIENTSIGNAL_MULTIPLEXED_CONNECTION = getattr(settings, 
        'CLIENTSIGNAL_MULTIPLEXED_CONNECTION',
        CLIENTSIGNAL_MULTIPLEXED_CONNECTION_DEFAULT)
CLIENTSIGNAL_BASE_SIGNALCONNECTION = getattr(settings, 
        'CLIENTSIGNAL_BASE_SIGNALCONNECTION',
        CLIENTSIGNAL_BASE_SIGNALCONNECTION_DEFAULT)


CLIENTSIGNAL_DEFAULT_ENCODER_DEFAULT = 'clientsignal.SignalEncoder'
CLIENTSIGNAL_OBJECT_HOOK_DEFAULT = 'clientsignal.signal_object_hook'

CLIENTSIGNAL_DEFAULT_ENCODER = getattr(settings, 
        'CLIENTSIGNAL_DEFAULT_ENCODER',
        CLIENTSIGNAL_DEFAULT_ENCODER_DEFAULT)
CLIENTSIGNAL_OBJECT_HOOK = getattr(settings, 
        'CLIENTSIGNAL_OBJECT_HOOK',
        CLIENTSIGNAL_OBJECT_HOOK_DEFAULT)