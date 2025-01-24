import csv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, wait
import sched
import time
from Counter import Counter
from TimingError import TimingError
import requests
import json
import sys
import os
import importlib

import argparse
import argcomplete

import logging
logger = logging.getLogger(__name__)

def do_requests(event, stats, local_latency_stats):
    global processed_requests, last_print_time_ms, error_requests, pending_requests
    processed_requests.increase()
    try:
        now_ms = time.time_ns() // 1_000_000
        
        url = f"{host_url_before_service}{event['ingress_service']}{host_url_after_service}"
        logging.debug(f"POSTing trace '{event['trace_id']}' to '{url}'")

        if dry_run:
            pending_requests.decrease()
            req_latency_ms = 1
            stats.append(f"{now_ms} \t {req_latency_ms} \t 200 \t {processed_requests.value} \t {pending_requests.value}")
        else:
            r = requests.post(url, event['as_json'])
            pending_requests.decrease()
            
            if r.status_code != 200:
                logging.error(f"Response Status Code {r.status_code}")
                error_requests.increase()

            req_latency_ms = int(r.elapsed.total_seconds()*1000)
            stats.append(f"{now_ms} \t {req_latency_ms} \t {r.status_code} \t {processed_requests.value} \t {pending_requests.value}")
        
        local_latency_stats.append(req_latency_ms)
        
        if now_ms > last_print_time_ms + 1_000:
            logging.info(f"Processed request {processed_requests.value}, latency {req_latency_ms}, pending requests {pending_requests.value}")
            last_print_time_ms = now_ms
        return event['timestamp'], req_latency_ms
    except Exception as err:
        logging.error("Error: %s" % err)

def job_assignment(v_pool, v_futures, event, stats, local_latency_stats):
    global timing_error_requests, pending_requests
    try:
        worker = v_pool.submit(do_requests, event, stats, local_latency_stats)
        v_futures.append(worker)
        pending_requests.increase()
        if pending_requests.value > threads: 
            # maximum capacity of thread pool reached, request is queued (not an issue for greedy runner)
            timing_error_requests += 1
            raise TimingError(event['timestamp'])
    except TimingError as err:
        logging.error("Error: %s" % err)

def file_runner(workload=None):
    global start_time, stats, local_latency_stats

    stats = list()
    logging.info("###############################################")
    logging.info("############   Run Forrest Run!!   ############")
    logging.info("###############################################")
    if len(sys.argv) > 1 and workload is None:
        workload_file = sys.argv[1]
    else:
        workload_file = workload

    csv_headers = ['timestamp', 'trace_id', 'ingress_service', 'as_json']
    logging.debug(f"Using headers: {csv_headers}")
    workload = []
    with open(workload_file) as f:
        logging.debug(f"Opening workload file '{workload_file}'")
        c = 0
        reader = csv.DictReader(f, fieldnames=csv_headers, delimiter=csv_files_delimiter)
        _ = next(reader, None)
        for row in reader:
            row['timestamp'] = int(row['timestamp'])
            workload.append(row)
            c += 1
        logging.info(f"Imported {c} entries from '{workload_file}'")

    s = sched.scheduler(time.time, time.sleep)
    pool = ThreadPoolExecutor(threads)
    futures = list()

    for event in workload:
        s.enter(event["timestamp"]/1000, 1, job_assignment, argument=(pool, futures, event, stats, local_latency_stats))

    start_time = time.time()
    logging.info("Start Time: %s", datetime.now().strftime("%H:%M:%S.%f - %g/%m/%Y"))
    s.run()

    wait(futures)
    run_duration_sec = time.time() - start_time
    avg_latency = 1.0*sum(local_latency_stats)/len(local_latency_stats)

    logging.info("###############################################")
    logging.info("###########   Stop Forrest Stop!!   ###########")
    logging.info("###############################################")
    logging.info("Run Duration (sec): %.6f", run_duration_sec)
    logging.info("Total Requests: %d - Error Request: %d - Timing Error Requests: %d - Average Latency (ms): %.6f - Request rate (req/sec) %.6f" % (len(workload), error_requests.value, timing_error_requests, avg_latency, 1.0*len(workload)/run_duration_sec))

    if run_after_workload is not None:
        logging.debug("Running 'after_workload' hooks")
        args = {"run_duration_sec": run_duration_sec,
                "last_print_time_ms": last_print_time_ms,
                "requests_processed": processed_requests.value,
                "timing_error_number": timing_error_requests,
                "total_request": len(workload),
                "error_request": error_requests.value,
                "runner_results_file": f"{output_path}/{result_file}_{workload_var.split('/')[-1].split('.')[0]}.txt"
                }
        run_after_workload(args)

### Main

RUNNER_PATH = os.path.dirname(os.path.abspath(__file__))
parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config-file', action='store', dest='parameters_file',
                    help='The Runner Parameters file', default=f'{RUNNER_PATH}/RunnerParameters.json')
parser.add_argument('-ll', '--log-level', action='store', dest='log_level',
                    help='Log Level', default='INFO')

argcomplete.autocomplete(parser)

try:
    args = parser.parse_args()
except ImportError:
    logging.error("Import error, there are missing dependencies to install.  'apt-get install python3-argcomplete "
          "&& activate-global-python-argcomplete3' may solve")
except AttributeError:
    parser.print_help()
except Exception as err:
    logging.error("Error:", err)

logging.basicConfig(level=args.log_level)
parameters_file_path = args.parameters_file


last_print_time_ms = 0
run_after_workload = None
timing_error_requests = 0
processed_requests = Counter()
error_requests = Counter()
pending_requests = Counter()


try:
    with open(parameters_file_path) as f:
        params = json.load(f)
    runner_parameters = params['RunnerParameters']
    host_url_before_service = runner_parameters["host_url_before_service"] # nginx access gateway ip
    host_url_after_service = runner_parameters["host_url_after_service"] # nginx access gateway ip
    workloads = runner_parameters["workload_files_path_list"] 
    csv_files_delimiter = runner_parameters["csv_files_delimiter"] 
    dry_run = runner_parameters["dry_run"] 
    threads = runner_parameters["thread_pool_size"] # n. parallel threads
    result_file = runner_parameters["result_file"]  # number of repetition rounds
    if "OutputPath" in params.keys() and len(params["OutputPath"]) > 0:
        output_path = params["OutputPath"]
        if output_path.endswith("/"):
            output_path = output_path[:-1]
        if not os.path.exists(output_path):
            os.makedirs(output_path)
    else:
        output_path = RUNNER_PATH
    if "AfterWorkloadFunction" in params.keys() and len(params["AfterWorkloadFunction"]) > 0:
        sys.path.append(params["AfterWorkloadFunction"]["file_path"])
        run_after_workload = getattr(importlib.import_module(params["AfterWorkloadFunction"]["file_path"].split("/")[-1]),
                                     params["AfterWorkloadFunction"]["function_name"])

except Exception as err:
    logging.error("ERROR: in Runner Parameters,", err)
    exit(1)


## Check if "workloads" is a directory path, if so take all the workload files inside it
if os.path.isdir(workloads[0]):
    dir_workloads = workloads[0]
    workloads = list()
    src_files = os.listdir(dir_workloads)
    for file_name in src_files:
        full_file_name = os.path.join(dir_workloads, file_name)
        if os.path.isfile(full_file_name):
            workloads.append(full_file_name)

stats = list()
local_latency_stats = list()
start_time = 0.0

for cnt, workload_var in enumerate(workloads):
    logging.info("Using workload of: %s" % workload_var)
    processed_requests.value = 0
    timing_error_requests = 0
    error_requests.value = 0
    file_runner(workload_var)
    logging.info("***************************************")
    try:
        result_file_name = f"{output_path}/{result_file}_{workload_var.split('/')[-1].split('.')[0]}.txt"
        logging.debug("Writing results to file '{result_file_name}'")
        with open(result_file_name, "w") as f:
            f.writelines("\n".join(stats))
    except Exception as err:
        logging.error("ERROR: saving result file,", err)
        exit(1)

logging.info("###############################################")
logging.info("###########   DONE Forrest DONE!!   ###########")
logging.info("###############################################")
exit(0)
