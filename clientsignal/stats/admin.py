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

from django.contrib import admin

from django.shortcuts import render_to_response
from django.template import RequestContext

from django.contrib.admin.views.decorators import staff_member_required

import clientsignal.settings as app_settings

@staff_member_required
def stats_view(request, *args, **kwargs):
    hosts = app_settings.CLIENTSIGNAL_STATS['hosts']
    stats_url = [u 
            for u,c in app_settings.CLIENTSIGNAL_CONNECTIONS.items() 
            if c == app_settings.CLIENTSIGNAL_STATS['connectionClass']][0]
    
    return render_to_response('clientsignal_stats/admin/stats.html',
                              {'title': 'Client Signal Stats',
                               'STATS_HOSTS': hosts,
                               'STATS_URL': stats_url,},
                              RequestContext(request, {}))

try:
    admin.site.register_view('stats', stats_view, 'Client Signal Stats')
except AttributeError:
    pass

