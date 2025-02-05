from prometheus_client import start_http_server, CollectorRegistry, Summary, Gauge, Counter

import logging
logger = logging.getLogger(__name__)

global registry
registry = CollectorRegistry()

experiment_id_label = "experiment_id"
labelnames = [experiment_id_label]

global EXPERIMENT_MS_COUNT
EXPERIMENT_MS_COUNT = Gauge('mub_experiment_ms_count', 'How many microservices are involved in the experiment', labelnames=labelnames, registry=registry)

global EXPERIMENT_TRACE_COUNT
EXPERIMENT_TRACE_COUNT = Gauge('mub_experiment_trace_count', 'How many traces are used in the experiment', labelnames=labelnames, registry=registry)

global START_TIME_DEPLOYMENTS
START_TIME_DEPLOYMENTS = Gauge('mub_experiment_start_time_deployments', 'Timestamp when deployment of ms started', labelnames=labelnames, registry=registry, unit='seconds')

global START_TIME_TRACES
START_TIME_TRACES = Gauge('mub_experiment_start_time_traces', 'Timestamp when running traces started', labelnames=labelnames, registry=registry, unit='seconds')

global FINISHED_TIME
FINISHED_TIME = Gauge('mub_experiment_finished_time', 'Timestamp when all trace requests were completed', labelnames=labelnames, registry=registry, unit='seconds')

global FINISHED_TIME_ESTIMATED
FINISHED_TIME_ESTIMATED = Gauge('mub_experiment_finished_time_estimated', 'Estimated timestamp when all trace requests will be completed', labelnames=labelnames, registry=registry, unit='seconds')

# TODO: Will need to see how this performs with thousands of services. Might need to remove the 'service' label
global DEPLOYED_SERVICES
DEPLOYED_SERVICES = Counter('mub_deployed_services', 'Deployed Services', labelnames=[experiment_id_label, "service"], registry=registry)

global REQUEST_LATENCY_MS
REQUEST_LATENCY_MS = Summary('mub_request_latency', 'Request Latency (user perspective)', labelnames=[experiment_id_label, "ingress"], registry=registry, unit='milliseconds')

global PENDING_REQUESTS
PENDING_REQUESTS = Gauge('mub_pending_requests', 'Ongoing requests (user perspective, waiting for response)', labelnames=labelnames, registry=registry)

global TIMING_ERROR_REQUESTS
TIMING_ERROR_REQUESTS = Counter('mub_timing_error_requests', 'Requests not started in time due to missing threads', labelnames=labelnames, registry=registry)

global PROCESSED_REQUESTS
PROCESSED_REQUESTS = Counter('mub_processed_requests', 'Processed requests (user perspective)', labelnames=labelnames, registry=registry)

global ERROR_REQUESTS
ERROR_REQUESTS = Counter('mub_error_requests', 'Errored requests (user perspective)', labelnames=labelnames, registry=registry)

def start_server(http_port):
    start_http_server(http_port, '0.0.0.0', registry=registry)
