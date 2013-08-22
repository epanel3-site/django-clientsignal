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
#

from django.utils.functional import memoize
from django.utils.datastructures import SortedDict
from django.utils.importlib import import_module

from django.core.exceptions import ImproperlyConfigured

import clientsignal.settings as app_settings

__signalconnection = SortedDict()

def get_class_or_func(import_path):
    module, attr = import_path.rsplit('.', 1)
    try:
        mod = import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured('Error importing module %s: "%s"' %
                                   (module, e))

    try:
        imported = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define a "%s" '
                                   'class or function.' % (module, attr))

    return imported


def get_backend_url_parts(url):
    import urlparse
    from urllib import unquote

    parts = urlparse.urlparse(url)
    path = unquote(parts.path or '') or None
    
    parts_dict = {
                  'scheme': parts.scheme,
                  'host': getattr(parts, 'hostname', 'localhost'),
                  'port': parts.port,
                  'username': unquote(parts.username  or ''),
                  'password': unquote(parts.password or ''),
                  'path': path[1:] if path and path[0] == '/' else path,
                 }

    return parts_dict

