from prometheus_client import start_http_server, CollectorRegistry, Summary

import logging
logger = logging.getLogger(__name__)

global registry
registry = CollectorRegistry()

global REQUEST_LATENCY_MS
REQUEST_LATENCY_MS = Summary('mub_request_latency_milliseconds', 'Request Latency (user perspective)',['endpoint'], registry=registry)

def start_server(http_port):
    start_http_server(http_port, '0.0.0.0', registry=registry)
