/* -*- coding: utf-8 -*-
 *
 * Except where noted: 
 * Copyright 2012-2013 Will Barton. 
 * All rights reserved.
 * 
 * Redistribution and use in source and binary forms, with or without 
 * modification, are permitted provided that the following conditions
 * are met:
 * 
 *   1. Redistributions of source code must retain the above copyright 
 *      notice, this list of conditions and the following disclaimer.
 *   2. Redistributions in binary form must reproduce the above copyright 
 *      notice, this list of conditions and the following disclaimer in the 
 *      documentation and/or other materials provided with the distribution.
 *   3. The name of the author may not be used to endorse or promote products
 *      derived from this software without specific prior written permission.
 * 
 * THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
 * INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
 * AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL
 * THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 * EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
 * PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
 * OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
 * OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
 * ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

// Based on https://github.com/joewalnes/reconnecting-websocket/
// MIT License:
//
// Copyright (c) 2010-2012, Joe Walnes
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
// THE SOFTWARE.
// 
// Ported to SockJS with some minor modifications.
var ReconnectingSocket = function(url, protocols) {
    protocols = protocols || ['websocket', 'xdr-streaming', 'xhr-streaming', 'iframe-eventsource', 'iframe-htmlfile', 'xdr-polling', 'xhr-polling', 'iframe-xhr-polling', 'jsonp-polling'];

    // Reconnecting Socket API
    this.reconnect = true;
    this.reconnectInterval = 1000;
    this.reconnectTimeout = 2000;
    this.debug = false;

    // WebSocket API
    this.url = url;
    this.readyState = SockJS.CONNECTING;
    this.protocol = undefined;
    this.binaryType = undefined;
    this.bufferedAmount = undefined;
    this.extensions = undefined;

    this.onopen = function(event) {
    };

    this.onclose = function(event) {
    };

    this.onconnecting = function(event) {
    };

    this.onmessage = function(event) {
    };

    this.onerror = function(event) {
    };

    this.send = function(data) {
        if (conn) {
            this.debug && window.console && console.log('send', url, data);
            return conn.send(data);
        } else {
            throw 'INVALID_STATE_ERR : Pausing to reconnect websocket';
        }
    };

    this.close = function() {
        if (conn) {
            forcedClose = true;
            conn.close();
        }
    };

    // Additional Public API
    this.refresh = function() {
        if (conn) {
            conn.close();
        }
    };
    
    // Private
    var conn = undefined;
    var timedOut = false;
    var forcedClose = false;
    
    var self = this;

    function connect(reconnectAttempt) {
        conn = new SockJS(url, protocols);
        
        self.onconnecting();
        self.debug && window.console && console.log('attempt-connect', url);
        
        var localConn = conn;
        var timeout = null;
        if (self.timeoutInterval > 0) {
            setTimeout(function() {
                self.debug && window.console && console.log('connection-timeout', url);
                timedOut = true;
                localConn.close();
                timedOut = false;
            }, self.timeoutInterval);
        }
        
        conn.onopen = function(event) {
            clearTimeout(timeout);
            self.debug && window.console && console.log('onopen', url);
            self.readyState = SockJS.OPEN;
            reconnectAttempt = false;
            self.onopen(event);
        };
        
        conn.onclose = function(event) {
            self.debug && window.console && console.log("onclose", url, event);
            clearTimeout(timeout);
            conn = null;
            if (forcedClose) {
                self.readyState = SockJS.CLOSED;
                self.onclose(event);
            } else {
                self.readyState = SockJS.CONNECTING;
                self.onconnecting();
                if (!reconnectAttempt && !timedOut) {
                    self.debug && window.console && console.log('onclose', url);
                    self.onclose(event);
                }
                setTimeout(function() {
                    connect(true);
                }, self.reconnectInterval);
            }
        };

        conn.onmessage = function(event) {
            self.debug && window.console && console.log('onmessage', url, event.data);
        	self.onmessage(event);
        };

        conn.onerror = function(event) {
            self.debug && window.console && console.log('onerror', url, event);
            self.onerror(event);
        };
    }

    connect(url);
    
};


// Based on https://gist.github.com/ismasan/299789
// Use SignalSocket for Django signal handling via django-clientsignal.
//
//      var sock = new SignalSocket('/events');
// 
//      sock.on('open', function() {
//          sock.send("mysignalname", {'keywork': "argument"});
//      });
//
//      sock.on('asignal', function(data) {
//          // Handle signal 
//      });
// 
var SignalSocket = function(url) {
    var conn = new ReconnectingSocket(url);

    var callbacks = {};
    this.on = function(event_name, callback) {
        callbacks[event_name] = callbacks[event_name] || [];
        callbacks[event_name].push(callback);
        return this;
    };

    this.send = function(event_name, event_data){
        var payload = JSON.stringify({event:event_name, data:event_data});
        conn.send(payload);
        return this;
    };

    // dispatch to the right handlers
    conn.onmessage = function(evt){
        var json = JSON.parse(evt.data);
        dispatch(json.event, json.data);
    };

    conn.onclose = function() { dispatch('disconnect', null); };
    conn.onopen = function() { dispatch('connect', null); };

    var dispatch = function(event_name, message){
        var chain = callbacks[event_name];
        if(typeof chain == 'undefined') 
            return; 
        for(var i = 0; i < chain.length; i++){
            chain[i](message)
        }
    }
};

