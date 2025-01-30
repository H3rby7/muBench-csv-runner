import K8sYamlDeployer as K8sYamlDeployer
import K8sYamlFiles as K8sYamlFiles

import logging
logger = logging.getLogger(__name__)

def deploy_svc_job(runner_parameters, svc_name):
    """
    Deploy service Job to be used with the worker pool
    """
    yaml_dir_path = runner_parameters['yaml_dir_path']
    dry_run = runner_parameters['dry_run']
    try:
        logging.info(f"Deploying '{svc_name}'")
        list_of_yamls = K8sYamlFiles.get_yamls_for_svc(svc_name, yaml_dir_path)
        if dry_run:
            logging.debug("Dry-run, not deploying...")
        else:
            K8sYamlDeployer.deploy_items(list_of_yamls)
    except Exception as err:
        logging.error("Error: %s" % err)

def deploy_svc_cb(runner_parameters, v_pool, v_futures, svc_name):
    """
    Deploy service Callback to use with scheduler.enter
    """
    worker = v_pool.submit(deploy_svc_job, runner_parameters, svc_name)
    v_futures.append(worker)
