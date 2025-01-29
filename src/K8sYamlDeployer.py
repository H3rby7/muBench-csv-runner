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

from kubernetes import client
from kubernetes.client.rest import ApiException
import yaml
import json
import time

import logging
logger = logging.getLogger(__name__)

def deploy_items(file_paths):
    """
    Deploy file_paths (yamls) to Kubernetes
    """

    for yaml_path in file_paths:
        with open(yaml_path) as f:
            complete_yaml = yaml.load_all(f,Loader=yaml.FullLoader)
            for partial_yaml in complete_yaml:
                deploy_yaml(partial_yaml)

def deploy_yaml(yaml):
    """
    Deploy the given yaml file

    Supported YAML kinds:
    * Deployment
    * Service
    * Ingress
    * ConfigMap
    * ServiceMonitor
    """
    meta_ns = yaml["metadata"]["namespace"]
    meta_name = yaml["metadata"]["name"]

    try:
        if yaml["kind"] == "Deployment":
            k8s_apps_api = client.AppsV1Api()
            k8s_apps_api.create_namespaced_deployment(namespace=meta_ns, body=yaml)
            # api_response = k8s_apps_api.read_namespaced_deployment_status(name=meta_name, namespace=meta_ns)
            # while (api_response.status.ready_replicas != api_response.status.replicas):
            #     logger.debug(f"\n *** Waiting deployment {meta_name} ready ...*** \n")
            #     time.sleep(5)
            #     api_response = k8s_apps_api.read_namespaced_deployment_status(name=meta_name, namespace=meta_ns)
            logger.debug(f"Deployment {meta_name} created.")
        elif yaml["kind"] == "Service":
            k8s_core_api = client.CoreV1Api()
            k8s_core_api.create_namespaced_service(namespace=meta_ns, body=yaml)
            logger.debug(f"Service '{meta_name}' created.")
        elif yaml["kind"] == "Ingress":
            k8s_networking_api = client.NetworkingV1Api()
            k8s_networking_api.create_namespaced_ingress(namespace=meta_ns, body=yaml)
            logger.debug(f"Ingress '{meta_name}' created.")
        elif yaml["kind"] == "ConfigMap":
                k8s_core_api = client.CoreV1Api()
                k8s_core_api.create_namespaced_config_map(namespace=meta_ns, body=yaml)
                logger.debug(f"ConfigMap '{meta_name}' created.")
        elif yaml["kind"] == "ServiceMonitor":
                k8s_crd_api = client.CustomObjectsApi()
                k8s_crd_api.create_namespaced_custom_object(group="monitoring.coreos.com", version="v1", plural="servicemonitors", namespace=meta_ns, body=yaml)
                logger.info(f"ServiceMonitor '{meta_name}' created.")
                logger.info("---")
    except ApiException as err:
        api_exception_body = json.loads(err.body)
        logger.error(f"Exception raised deploying a {yaml['kind']}: {api_exception_body['details']} -> {api_exception_body['reason']}")
