from kubernetes import client, config
from kubernetes.client.rest import ApiException

import json
import time

import K8sYamlFiles as K8sYamlFiles
import K8sYamlDeployer as K8sYamlDeployer

import logging
logger = logging.getLogger(__name__)

config.load_kube_config()

def prepare_namespace(k8s_namespace, yaml_dir_path):
    """
    Prepare Kubernetes for the experiment

    1. Clear namespace by removing and re-creating it
    2. Create non-service-specific YAMLs
    """
    recreate_namespace(k8s_namespace)
    deploy_generic_yamls(yaml_dir_path)
    

def recreate_namespace(namespace):
    logging.debug(f"Preparing Kubernetes namespace: '{namespace}'")
    k8s_core_api = client.CoreV1Api()
    try:
        logging.debug(f"Deleting Kubernetes namespace: '{namespace}'")
        k8s_core_api.delete_namespace(name=namespace)
        logging.debug(f"Successfully deleted Kubernetes namespace: '{namespace}'")
    except ApiException as err:
        if err.status == 404:
            logger.debug(f"Kubernetes namespace: '{namespace}' did not exist - continue...")
        else:
            api_exception_body = json.loads(err.body)
            logger.fatal(f"Exception when deleting namespace {namespace}: {api_exception_body['details']} -> {api_exception_body['reason']}")
            exit(1)

    while not check_namespace_does_not_exist(k8s_core_api, namespace):
        logger.info(f"Waiting for namespace '{namespace}' to be deleted...")
        time.sleep(1)

    try:
        logging.debug(f"Creating Kubernetes namespace: '{namespace}'")
        k8s_core_api.create_namespace(client.V1Namespace(
            metadata=client.V1ObjectMeta(name=namespace)
        ))
        logging.debug(f"Successfully created Kubernetes namespace: '{namespace}'")
    except ApiException as err:
        api_exception_body = json.loads(err.body)
        logger.fatal(f"Exception when creating namespace {namespace}: {api_exception_body['details']} -> {api_exception_body['reason']}")
        exit(1)
    logging.info(f"Successfully prepared Kubernetes namespace: '{namespace}'")

def deploy_generic_yamls(yaml_dir_path):
    logging.debug(f"Searching for generic YAMLs in '{yaml_dir_path}'")
    generic_yamls = K8sYamlFiles.get_generic_yamls(yaml_dir_path)
    logging.info(f"Deploying generic YAMLs '{generic_yamls}'")
    K8sYamlDeployer.deploy_items(generic_yamls)

def check_namespace_does_not_exist(k8s_core_api, namespace):
    """
    Check if the given namespace does NOT exist, using the given k8s_core_api client
    """
    try:
        k8s_core_api.read_namespace(name=namespace)
    except ApiException as err:
        if err.status == 404:
            return True
    return False
