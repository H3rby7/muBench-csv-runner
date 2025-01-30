# BSD 4-Clause License

# Copyright (c) 2021, University of Rome Tor Vergata
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

#  * Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#  * All advertising materials mentioning features or use of this software
#    must display the following acknowledgement: This product includes
#    software developed by University of Rome Tor Vergata and its contributors.
#  * Neither the name of University of Rome Tor Vergata nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import time
from TimingError import TimingError
import requests
import stats
import Metrics

import logging
logger = logging.getLogger(__name__)

last_print_time_ms = 0

def run_trace_job(runner_parameters, trace_item, local_stats, local_latency_stats):
    """
    Run Trace Job to be used with the worker pool
    """
    global last_print_time_ms

    url_before_service = runner_parameters['url_before_service']
    url_after_service = runner_parameters['url_after_service']
    dry_run = runner_parameters['dry_run']
    service = trace_item['ingress_service']

    stats.processed_requests.increase()
    try:
        now_ms = time.time_ns() // 1_000_000
        
        url = f"{url_before_service}{service}{url_after_service}"
        body = trace_item['as_json']
        logging.debug(f"POSTing trace '{trace_item['trace_id']}'to '{url}' with body \n\t{body}")

        if dry_run:
            stats.pending_requests.decrease()
            req_latency_ms = 1

            Metrics.REQUEST_LATENCY_MS.labels(service).observe(req_latency_ms)
            local_stats.append(f"{now_ms} \t {req_latency_ms} \t 200 \t {stats.processed_requests.value} \t {stats.pending_requests.value}")
        else:
            r = requests.post(url, body, headers={"Content-Type":"application/json"})
            stats.pending_requests.decrease()
            
            if r.status_code == 200:
                logging.debug(f"POST for {url} returned http status {r.status_code}")
            else:
                logging.error(f"POST for {url} returned http status {r.status_code}")
                stats.error_requests.increase()

            req_latency_ms = int(r.elapsed.total_seconds()*1000)

            Metrics.REQUEST_LATENCY_MS.labels(service).observe(req_latency_ms)
            local_stats.append(f"{now_ms} \t {req_latency_ms} \t {r.status_code} \t {stats.processed_requests.value} \t {stats.pending_requests.value}")
        
        local_latency_stats.append(req_latency_ms)
        
        if now_ms > last_print_time_ms + 1_000:
            logging.info(f"Processed request {stats.processed_requests.value}, latency {req_latency_ms}, pending requests {stats.pending_requests.value}")
            last_print_time_ms = now_ms
        return trace_item['timestamp'], req_latency_ms
    except Exception as err:
        logging.error("Error: %s" % err)

def run_trace_cb(runner_parameters, v_pool, v_futures, trace_item, local_stats, local_latency_stats):
    """
    Run Trace Callback to use with scheduler.enter
    """
    thread_pool_size = runner_parameters['thread_pool_size']

    try:
        worker = v_pool.submit(run_trace_job, runner_parameters, trace_item, local_stats, local_latency_stats)
        v_futures.append(worker)
        stats.pending_requests.increase()
        if stats.pending_requests.value > thread_pool_size: 
            # maximum capacity of thread pool reached, request is queued (not an issue for greedy runner)
            stats.timing_error_requests.increase()
            raise TimingError(trace_item['timestamp'])
    except TimingError as err:
        logging.error("Error: %s" % err)
