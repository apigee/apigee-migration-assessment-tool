var request_start_time = context.getVariable('client.received.start.timestamp');
var target_start_time  = context.getVariable('target.sent.end.timestamp');
var target_end_time    = context.getVariable('target.received.start.timestamp');
var request_end_time   = context.getVariable('system.timestamp');
var total_request_time = String(request_end_time-request_start_time);
var total_target_time  = String(target_end_time-target_start_time);
var total_proxy_time   = String(total_request_time-total_target_time);

context.setVariable('flow.healthcheck.proxy.latency', total_proxy_time);
context.setVariable('flow.healthcheck.target.latency', total_target_time);
context.setVariable('flow.healthcheck.latency', total_request_time);
