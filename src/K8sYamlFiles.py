import os

import K8sYamlDeployer as K8sYamlDeployer

import logging
logger = logging.getLogger(__name__)

def get_yamls_for_svc(svc_name, yaml_dir):
    """
    Get all yamls for a given svc_name

    Looks for yaml files with the pattern `.+-ms-<svc_name>.yaml`
    """
    logger.debug(f"Looking for yaml files for service '{svc_name}' in '{yaml_dir}'")
    items = list()
    for r, d, f in os.walk(yaml_dir):
        for file in f:
            if f"{svc_name}.yaml" in file:
                items.append(os.path.join(r, file))
    logger.debug(f"Found YAML files for service '{svc_name}': '{items}'")
    return items

def get_generic_yamls(yaml_dir):
    """
    Get all yamls that are required for all services

    Looks for yaml files without the pattern `-ms-`
    """
    logger.debug(f"Looking for generic yaml files in '{yaml_dir}'")
    items = list()
    for r, d, f in os.walk(yaml_dir):
        for file in f:
            if f"ms-" in file:
                continue
            if f".yaml" in file:
                items.append(os.path.join(r, file))
    logger.debug(f"Found generic YAML files '{items}'")
    return items
