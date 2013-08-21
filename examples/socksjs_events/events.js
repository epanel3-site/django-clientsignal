
// Based on https://gist.github.com/ismasan/299789
var EventSocket = function(url){
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

    conn.onclose = function() { dispatch('close', null); };
    conn.onopen = function() { dispatch('open', null); };

    var dispatch = function(event_name, message){
        var chain = callbacks[event_name];
        if(typeof chain == 'undefined') 
            return; 
        for(var i = 0; i < chain.length; i++){
            chain[i](message)
        }
    }
};

