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

from collections import defaultdict
from collections import Counter

import tornado

from django.dispatch import Signal, receiver

import clientsignal.settings as app_settings

from clientsignal.conn import SimpleSignalConnection
from clientsignal.utils import get_class_or_func, get_routers

stat_broadcast = Signal(providing_args=["stats"])

class StatsSignalConnection(SimpleSignalConnection):

    def on_open(self, connection_info):
        super(StatsSignalConnection, self).on_open(connection_info)

        period = app_settings.CLIENTSIGNAL_STATS['period'] 
        self.loop = tornado.ioloop.PeriodicCallback(self._send_stats,
                period)
        self.loop.start()

    def on_close(self):
        super(StatsSignalConnection, self).on_close()
        self.loop.stop()

    def _send_stats(self):
        routers = get_routers()
        router_stats_dicts = [r.stats.dump() for r in routers if
                r._connection in stat_connections]
        router_stats = sum( 
                (Counter(dict(x)) for x in router_stats_dicts),
                Counter())

        clients_list = [(c.request.user.username, c.__class__.__name__)
                        for c in StatsSignalConnection.clients
                        if c.__class__ in stat_connections]
        clients = defaultdict(list)
        [clients[k].append(v) for v, k in clients_list]

        stats = {
                'server': router_stats,
                'clients': clients.items(),
                }
        stat_broadcast.send(sender=None, stats=stats)

StatsSignalConnection.broadcast('stat_broadcast', stat_broadcast)

stat_connections = [get_class_or_func(c) for c in
        app_settings.CLIENTSIGNAL_STATS['connections']]

