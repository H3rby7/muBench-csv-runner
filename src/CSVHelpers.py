import csv

import logging
logger = logging.getLogger(__name__)

def read_trace_csv(workload_file, csv_files_delimiter):
    """
    Return traces from CSV file
    """
    csv_headers = ['timestamp', 'trace_id', 'ingress_service', 'as_json']
    logging.info(f"Using headers: {csv_headers} for workload file '{workload_file}'")
    workload = []
    with open(workload_file) as f:
        c = 0
        reader = csv.DictReader(f, fieldnames=csv_headers, delimiter=csv_files_delimiter)
        # Skip the first line (as it is just the headers)
        _ = next(reader, None)
        for row in reader:
            row['timestamp'] = int(row['timestamp'])
            workload.append(row)
            c += 1
        logging.info(f"Imported {c} traces from '{workload_file}'")
    return workload

def read_deployment_csv(deployment_ts_file, csv_files_delimiter):
    """
    Return deployments with timestamp from CSV file
    """
    csv_headers = ['ms', 'required_at']
    logging.info(f"Using headers: {csv_headers} for timestamp file '{deployment_ts_file}'")
    deployments = []
    with open(deployment_ts_file) as f:
        c = 0
        reader = csv.DictReader(f, fieldnames=csv_headers, delimiter=csv_files_delimiter)
        # Skip the first line (as it is just the headers)
        _ = next(reader, None)
        for row in reader:
            row['required_at'] = int(row['required_at'])
            deployments.append(row)
            c += 1
        logging.info(f"Imported {c} deployment entries from '{deployment_ts_file}'")
    return deployments
