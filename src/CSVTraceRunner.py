from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, wait
import sched
import time

import json
import sys
import os
import importlib

import stats
import Metrics

import argparse
import argcomplete

from kubernetes import config

import CSVHelpers as CSVHelpers
import K8sPrepare as K8sPrepare
import TraceJob as TraceJob
import DeployJob as DeployJob

import logging
logger = logging.getLogger(__name__)

def file_runner(runner_parameters, runner_results_file):
    global start_time, local_stats, local_latency_stats

    traces_file_path = runner_parameters["traces_file_path"] # traces.csv file path
    deployment_ts_file_path = runner_parameters["deployment_ts_file_path"] # deployment_ts.csv file path
    deployments_headstart_in_s = runner_parameters["deployments_headstart_in_s"] # headstart for deployments prior to the first use of the service
    yaml_dir_path = runner_parameters["yaml_dir_path"] # traces.csv file path
    k8s_namespace = runner_parameters["k8s_namespace"] # experiment namespace in kubernetes
    dry_run = runner_parameters["dry_run"] # only local testing, no outgoing calls
    csv_files_delimiter = runner_parameters["csv_files_delimiter"]
    thread_pool_size = runner_parameters['thread_pool_size']

    local_stats = list()
    logging.info("###############################################")
    logging.info("############   Run Forrest Run!!   ############")
    logging.info("###############################################")

    s = sched.scheduler(time.time, time.sleep)
    pool = ThreadPoolExecutor(thread_pool_size)
    futures = list()

    if dry_run:
        logging.debug("Dry-run, no kubernetes to prepare, sleeping shortly to be realistic")
        time.sleep(5)
    else:
        K8sPrepare.prepare_namespace(k8s_namespace, yaml_dir_path)

    logging.info("Reading in and scheduling deployments")
    deployment_ts = CSVHelpers.read_deployment_csv(deployment_ts_file_path, csv_files_delimiter)
    Metrics.EXPERIMENT_MS_COUNT.set(len(deployment_ts))
    for event in deployment_ts:
        # 'enter' takes the schedule time in seconds, so we divide our MS value by 1000.
        s.enter(event["required_at"]/1000, 1, DeployJob.deploy_svc_cb, argument=(runner_parameters, pool, futures, event['ms']))

    logging.info("Reading in and scheduling traces")
    workload = CSVHelpers.read_trace_csv(traces_file_path, csv_files_delimiter)
    Metrics.EXPERIMENT_TRACE_COUNT.set(len(workload))
    max_ev_ts = 0
    for event in workload:
        # 'enter' takes the schedule time in seconds, so we divide our MS value by 1000.
        # Also delay trace scheduling by 'deployments_headstart_in_s' to ensure services are ready.
        ev_ts = (event["timestamp"]/1000) + deployments_headstart_in_s
        if (ev_ts > max_ev_ts):
            max_ev_ts = ev_ts
        s.enter(ev_ts, 2, TraceJob.run_trace_cb, argument=(runner_parameters, pool, futures, event, local_stats, local_latency_stats))

    start_time = time.time()
    Metrics.START_TIME_DEPLOYMENTS.set(start_time)
    logging.info("Start Time: %s", datetime.fromtimestamp(start_time).strftime("%H:%M:%S.%f - %g/%m/%Y"))

    logging.info(f"Deployments headstart is {deployments_headstart_in_s} seconds")

    trace_start_time = start_time + deployments_headstart_in_s
    Metrics.START_TIME_TRACES.set(trace_start_time)
    logging.info("Estimated trace start: %s", datetime.fromtimestamp(trace_start_time).strftime("%H:%M:%S.%f - %g/%m/%Y"))

    finished_time_estimated = start_time + max_ev_ts
    Metrics.FINISHED_TIME_ESTIMATED.set(finished_time_estimated)
    logging.info("Estimated duration (sec): %.0f", max_ev_ts)
    logging.info("Estimated end time: %s", datetime.fromtimestamp(finished_time_estimated).strftime("%H:%M:%S.%f - %g/%m/%Y"))
    s.run()

    wait(futures)

    finished_time = time.time()
    Metrics.FINISHED_TIME.set(finished_time)

    run_duration_sec = finished_time - start_time
    avg_latency = 1.0*sum(local_latency_stats)/len(local_latency_stats)

    logging.info("###############################################")
    logging.info("###########   Stop Forrest Stop!!   ###########")
    logging.info("###############################################")
    logging.info("Run Duration (sec): %.6f", run_duration_sec)
    logging.info("Total Requests: %d - Error Request: %d - Timing Error Requests: %d - Average Latency (ms): %.6f - Request rate (req/sec) %.6f" % (len(workload), stats.error_requests.value, stats.timing_error_requests.value, avg_latency, 1.0*len(workload)/run_duration_sec))

    if run_after_workload is not None:
        logging.debug("Running 'after_workload' hooks")
        args = {"run_duration_sec": run_duration_sec,
                "requests_processed": stats.processed_requests.value,
                "timing_error_number": stats.timing_error_requests.value,
                "total_request": len(workload),
                "error_request": stats.error_requests.value,
                "runner_results_file": runner_results_file
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

run_after_workload = None

try:
    with open(parameters_file_path) as f:
        params = json.load(f)

    if params['in_cluster']:
        logger.info("Using Kubernetes in_cluster config")
        config.load_incluster_config()
    else:
        logger.info("Using Kubernetes file config")
        config.load_kube_config()

    runner_parameters = params['RunnerParameters']

    result_file_prefix = params["ResultFilePrefix"]
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

local_stats = list()
local_latency_stats = list()
start_time = 0.0

stats.processed_requests.value = 0
stats.timing_error_requests.value = 0
stats.error_requests.value = 0

timestr = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
runner_results_file = f"{output_path}/{result_file_prefix}_{timestr}.csv"

Metrics.start_server(8080)

# file_runner is a blocking call
file_runner(runner_parameters, runner_results_file)
# so the code after this is executed when file_runner is done.

try:
    logging.debug("Writing results to file '%s'", runner_results_file)
    with open(runner_results_file, "w") as f:
        f.writelines("\t".join(["timestamp", "trace_rt_ms", "trace_http_status", "processed_requests", "pending_requests"]))
        f.writelines("\n")
        f.writelines("\n".join(local_stats))
except Exception as err:
    logging.error("ERROR: saving result file,", err)
    exit(1)

logging.info("###############################################")
logging.info("###########   DONE Forrest DONE!!   ###########")
logging.info("###############################################")
time.sleep(1)
exit(0)
