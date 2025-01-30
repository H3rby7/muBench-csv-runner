from prometheus_client import start_http_server, CollectorRegistry, Summary, Gauge, Counter

import logging
logger = logging.getLogger(__name__)

global registry
registry = CollectorRegistry()

global EXPERIMENT_MS_COUNT
EXPERIMENT_MS_COUNT = Gauge('mub_experiment_ms_count', 'How many microservices are involved in the experiment', registry=registry)

global EXPERIMENT_TRACE_COUNT
EXPERIMENT_TRACE_COUNT = Gauge('mub_experiment_trace_count', 'How many traces are used in the experiment', registry=registry)

# TODO: Will need to see how this performs with thousands of services. Might need to remove the 'service' label
global DEPLOYED_SERVICES
DEPLOYED_SERVICES = Counter('mub_deployed_services', 'Deployed Services', labelnames=["service"], registry=registry)

global REQUEST_LATENCY_MS
REQUEST_LATENCY_MS = Summary('mub_request_latency_milliseconds', 'Request Latency (user perspective)', labelnames=["ingress"], registry=registry, unit='millis')

global PENDING_REQUESTS
PENDING_REQUESTS = Gauge('mub_pending_requests', 'Ongoing requests (user perspective, waiting for response)', registry=registry)

global TIMING_ERROR_REQUESTS
TIMING_ERROR_REQUESTS = Counter('mub_timing_error_requests', 'Requests not started in time due to missing threads', registry=registry)

global PROCESSED_REQUESTS
PROCESSED_REQUESTS = Counter('mub_processed_requests', 'Processed requests (user perspective)', registry=registry)

global ERROR_REQUESTS
ERROR_REQUESTS = Counter('mub_error_requests', 'Errored requests (user perspective)', registry=registry)

def start_server(http_port):
    start_http_server(http_port, '0.0.0.0', registry=registry)
