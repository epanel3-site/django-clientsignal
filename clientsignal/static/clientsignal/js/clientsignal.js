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
    var conn = new SockJS(url);

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

