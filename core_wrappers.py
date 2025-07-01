#!/usr/bin/python

# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License

"""Provides core wrapper functions for the Apigee migration assessment
    tool.

This module orchestrates the key steps involved in assessing an Apigee
setup for migration. It handles pre-validation checks, exporting
artifacts from the source Apigee environment, validating these
artifacts against the target environment's constraints, visualizing
the dependencies, generating a qualification report, and
determining the source environment's topology.

Key Functions:

- `pre_validation_checks`: Performs checks on the input configuration.
- `export_artifacts`: Exports artifacts from the source Apigee instance.
- `validate_artifacts`: Validates the exported artifacts against the
                        target environment.
- `visualize_artifacts`: Creates a visual representation of the
                        artifact dependencies.
- `qualification_report`: Generates a comprehensive report summarizing
                        the assessment findings.
- `get_topology`: Determines the topology of the source
                    Apigee OPDK installation.

Constants:

- `seperator`: String used as a separator in reports.
- `DEFAULT_GCP_ENV_TYPE`: Default GCP environment type.
"""

import os
from pyvis.network import Network  # pylint: disable=E0401
import networkx as nx  # pylint: disable=E0401
from exporter import ApigeeExporter
from classic import ApigeeClassic
from nextgen import ApigeeNewGen
from validator import ApigeeValidator
from qualification_report import QualificationReport
from topology import ApigeeTopology
from utils import (
    create_dir, get_source_auth_token,
    get_access_token, write_json, parse_json, parse_config)
import sharding
from base_logger import logger


SEPERATOR = ' | '
DEFAULT_GCP_ENV_TYPE = 'ENVIRONMENT_TYPE_UNSPECIFIED'


def pre_validation_checks(cfg):  # pylint: disable=R0914
    """Performs pre-validation checks on the input configuration.

    This function validates the provided configuration `cfg` to ensure
    that all required keys are present and that the source and target
    Apigee organizations exist. It checks `input.properties` for
    mandatory keys and verifies connectivity to both source and target
    organizations.

    Args:
        cfg (configparser.ConfigParser): The parsed configuration
                                        from input.properties.

    Returns:
        bool: True if all checks pass, False otherwise.
    """
    logger.info(
        "------------------- Pre Validation Checks -----------------------")

    # validate input.properties
    required_keys = {
        "inputs": [
            "SOURCE_URL", "SOURCE_ORG", "SOURCE_AUTH_TYPE",
            "SOURCE_APIGEE_VERSION", "TARGET_URL", "GCP_PROJECT_ID",
            "TARGET_DIR", "SSL_VERIFICATION"],
    }
    missing_keys = []

    for section, keys in required_keys.items():
        if section in cfg:
            section_keys = cfg[section]
            for key in keys:
                if key not in section_keys:
                    missing_keys.append((section, key))
        else:
            logger.error(f"Section {section} is missing in input.properties")  # noqa pylint: disable=W1203
            return False

    if missing_keys:
        logger.error("Missing keys in input.properties:")
        for section, key in missing_keys:
            logger.error(f" - Section: {section}, Key: {key}")  # noqa pylint: disable=W1203
        return False
    logger.info("All required keys are present in input.properties")

    # check for source org
    source_url = cfg.get('inputs', 'SOURCE_URL')
    source_org = cfg.get('inputs', 'SOURCE_ORG')
    source_auth_token = get_source_auth_token()
    source_auth_type = cfg.get('inputs', 'SOURCE_AUTH_TYPE')
    ssl_verification = cfg.getboolean('inputs', 'SSL_VERIFICATION',
                                      fallback=True)
    opdk = ApigeeClassic(source_url, source_org,
                         source_auth_token, source_auth_type, ssl_verification)
    if not opdk.get_org():
        logger.error("No source organizations found")
        return False

    # check for target org
    target_url = cfg.get('inputs', 'TARGET_URL')
    gcp_project_id = cfg.get('inputs', 'GCP_PROJECT_ID')
    gcp_token = get_access_token()
    gcp_env_type = DEFAULT_GCP_ENV_TYPE

    xorhybrid = ApigeeNewGen(target_url, gcp_project_id,
                             gcp_token, gcp_env_type)
    missing_permissions = xorhybrid.validate_permissions()
    if len(missing_permissions) > 0:
        logger.error(    # pylint: disable=W1203
            f"Missing required IAM permission. ERROR-INFO - {missing_permissions}")  # noqa pylint: disable=C0301,W1203
        logger.info("Ensure user/service account has roles/apigee.readOnlyAdmin role and apigee.proxies.create permission")  # noqa pylint: disable=C0301,W1203
        return False
    org_obj = xorhybrid.get_org()
    if org_obj.get("error"):
        logger.error(    # pylint: disable=W1203
            f"No target organizations found. ERROR-INFO - {org_obj['error'].get('message','No error Info found.')}")  # noqa pylint: disable=C0301,W1203
        return False
    return True


def export_artifacts(cfg, resources_list):
    """Exports artifacts from the source Apigee environment.

    Exports specified Apigee artifacts (proxies, shared flows, etc.)
    from the source environment based on the provided configuration
    and resource list. It handles the creation of necessary directories,
    orchestrates the export process, and manages dependencies between
    artifacts.

    Args:
        cfg (configparser.ConfigParser): The parsed configuration from
                                        input.properties.
        resources_list (list): A list of resource types to export.

    Returns:
        dict: A dictionary containing the exported artifact data.
    """
    logger.info('------------------- EXPORT -----------------------')
    backend_cfg = parse_config('backend.properties')
    source_url = cfg.get('inputs', 'SOURCE_URL')
    source_org = cfg.get('inputs', 'SOURCE_ORG')
    source_auth_token = get_source_auth_token()
    source_auth_type = cfg.get('inputs', 'SOURCE_AUTH_TYPE')
    target_dir = cfg.get('inputs', 'TARGET_DIR')
    try:
        ssl_verification = cfg.getboolean('inputs', 'SSL_VERIFICATION')
    except ValueError:
        ssl_verification = True
    export_dir = f"{target_dir}/{backend_cfg.get('export', 'EXPORT_DIR')}"
    api_export_dir = f"{export_dir}/apis"
    sf_export_dir = f"{export_dir}/sharedflows"
    create_dir(api_export_dir)
    create_dir(sf_export_dir)
    apigee_export = ApigeeExporter(
        source_url,
        source_org,
        source_auth_token,
        source_auth_type,
        ssl_verification
    )
    if os.environ.get("IGNORE_EXPORT") == "true":
        export_data = {}
        export_data["orgConfig"] = apigee_export.read_export_state(os.path.join(export_dir,"orgConfig"))  # noqa pylint: disable=C0301
        export_data["envConfig"] = apigee_export.read_export_state(os.path.join(export_dir,"envConfig"))  # noqa pylint: disable=C0301
    else:
        export_data = apigee_export.get_export_data(resources_list, export_dir)
        logger.debug(export_data)
        apigee_export.create_export_state(export_dir)
    proxy_dependency_map = sharding.proxy_dependency_map(cfg, export_data)
    export_data['proxy_dependency_map'] = proxy_dependency_map
    if not os.environ.get("IGNORE_ENV_SHARD") == "true":
        sharding_output = sharding.sharding_wrapper(
            proxy_dependency_map, export_data)
        export_data['sharding_output'] = sharding_output
    return export_data


def validate_artifacts(cfg, resources_list, export_data):  # noqa pylint: disable=R0914,R0912,R0915
    """Validates exported artifacts against the target environment.

    Validates the exported Apigee artifacts against the constraints of
    the target environment. This includes checks for compatibility,
    supported features, and potential issues that might arise during
    migration.  It generates a CSV report summarizing the validation
    results.

    Args:
        cfg (configparser.ConfigParser): The parsed configuration from
                                        input.properties.
        export_data (dict): A dictionary containing the exported artifact
                            data.

    Returns:
        dict: A dictionary containing the validation report.
    """
    logger.info('------------------- VALIDATE -----------------------')
    backend_cfg = parse_config('backend.properties')
    report = {}
    target_dir = cfg.get('inputs', 'TARGET_DIR')
    export_dir = f"{target_dir}/{backend_cfg.get('export', 'EXPORT_DIR')}"
    target_export_dir = f"{target_dir}/target"
    target_export_data_file = f"{target_export_dir}/export_data.json"
    api_export_dir = f"{target_export_dir}/apis"
    sf_export_dir = f"{target_export_dir}/sharedflows"
    create_dir(api_export_dir)
    create_dir(sf_export_dir)
    target_url = cfg.get('inputs', 'TARGET_URL')
    gcp_project_id = cfg.get('inputs', 'GCP_PROJECT_ID')
    gcp_env_type = DEFAULT_GCP_ENV_TYPE
    gcp_token = get_access_token()
    apigee_export = ApigeeExporter(
        target_url,
        gcp_project_id,
        gcp_token,
        'oauth',
        True
    )
    target_compare = cfg.getboolean('inputs', 'TARGET_COMPARE', fallback=False)
    target_resources = ['targetservers', 'flowhooks', 'resourcefiles',
                        'apis', 'sharedflows', 'org_keyvaluemaps',
                        'keyvaluemaps', 'apps', 'apiproducts',
                        'developers']
    target_resource_list = []
    if 'all' in resources_list:
        target_resource_list = target_resources
    else:
        target_resource_list = [ r for r in resources_list if r in target_resources]  # noqa pylint: disable=C0301
    target_export_data = parse_json(target_export_data_file)
    if target_compare and (not target_export_data.get('export', False)):
        target_export_data = apigee_export.get_export_data(target_resource_list, target_export_dir)  # noqa pylint: disable=C0301
        target_export_data['export'] = True
        write_json(target_export_data_file, target_export_data)
    apigee_validator = ApigeeValidator(target_url, gcp_project_id, gcp_token, gcp_env_type, target_export_data, target_compare)  # noqa pylint: disable=C0301

    for env, _ in export_data['envConfig'].items():
        logger.info(f'Environment -- {env}')  # pylint: disable=W1203
        target_servers = export_data['envConfig'][env]['targetServers']
        resourcefiles = export_data['envConfig'][env]['resourcefiles']
        flowhooks = export_data['envConfig'][env]['flowhooks']
        keyvaluemaps = export_data['envConfig'][env]['kvms']
        if 'all' in resources_list or 'keyvaluemaps' in resources_list:
            report[env + SEPERATOR +
                'targetServers'] = apigee_validator.validate_env_targetservers(env, target_servers)  # noqa pylint: disable=C0301
        if 'all' in resources_list or 'resourcefiles' in resources_list:
            report[env + SEPERATOR +
               'resourcefiles'] = apigee_validator.validate_env_resourcefiles(env, resourcefiles)  # noqa pylint: disable=C0301
        if 'all' in resources_list or 'flowhooks' in resources_list:
            report[env + SEPERATOR +
               'flowhooks'] = apigee_validator.validate_env_flowhooks(env, flowhooks)  # noqa
        if 'all' in resources_list or 'keyvaluemaps' in resources_list:
            report[env + SEPERATOR +
               'keyvaluemaps'] = apigee_validator.validate_kvms(env, keyvaluemaps)  # noqa

    if 'all' in resources_list or 'org_keyvaluemaps' in resources_list:
        org_keyvaluemaps = export_data['orgConfig']['kvms']
        report['org_keyvaluemaps'] = apigee_validator.validate_kvms(None, org_keyvaluemaps)  # noqa
    if 'all' in resources_list or 'developers' in resources_list:
        developers = export_data['orgConfig']['developers']
        report['developers'] = apigee_validator.validate_org_resource('developers', developers)  # noqa pylint: disable=C0301
    if 'all' in resources_list or 'apiproducts' in resources_list:
        api_products = export_data['orgConfig']['apiProducts']
        report['apiProducts'] = apigee_validator.validate_org_resource('apiProducts', api_products)  # noqa pylint: disable=C0301
    if 'all' in resources_list or 'apps' in resources_list:
        apps = export_data['orgConfig']['apps']
        report['apps'] = apigee_validator.validate_org_resource('apps', apps)  # noqa pylint: disable=C0301
    if 'all' in resources_list or 'apis' in resources_list:
        apis = export_data.get('orgConfig', {}).get('apis', {}).keys()    # noqa pylint: disable=C0301
        apis_validation = apigee_validator.validate_proxy_bundles(apis, export_dir, 'apis')  # noqa pylint: disable=C0301
        # Todo  # pylint: disable=W0511
        # validate proxy unifier output bundles
        report.update(apis_validation)
    if 'all' in resources_list or 'sharedflows' in resources_list:
        sharedflows = export_data.get('orgConfig', {}).get('sharedflows', {}).keys()    # noqa pylint: disable=C0301
        sf_validation = apigee_validator.validate_proxy_bundles(sharedflows, export_dir, 'sharedflows')  # noqa pylint: disable=C0301
        # Todo  # pylint: disable=W0511
        # validate proxy unifier output bundles
        report.update(sf_validation)
    return report


def visualize_artifacts(cfg, export_data, report):    # noqa pylint: disable=R0914,R0912,R0915
    """Visualizes artifact dependencies and validation results.

    Creates an interactive HTML visualization of the exported Apigee
    artifacts, their dependencies, and the validation results.
    The visualization helps to understand the relationships between
    different components and identify potential migration challenges.

    Args:
        cfg (configparser.ConfigParser): The parsed configuration from
                                        input.properties.
        export_data (dict): A dictionary containing the exported
                            artifact data.
        report (dict): A dictionary containing the validation report.

    Returns:
        None
    """
    logger.info('------------------- VISUALIZE -----------------------')
    backend_cfg = parse_config('backend.properties')
    source_url = cfg.get('inputs', 'SOURCE_ORG')
    source_ui_url = 'https://console.cloud.google.com'
    api_url = 'https://apigee.googleapis.com/v1'
    exportorg = export_data['orgConfig']
    exportenv = export_data['envConfig']
    dg = nx.DiGraph()
    report.pop('report')
    # Process the report
    final_report = {}
    for res, val in report.items():
        final_report[res] = {}
        for i in val:
            if i.get('importable', False):
                final_report[res][i['name']] = i.get('importable', False)
            else:
                violations = i.get('reason', [{'violations': []}])
                if len(violations[0].get('violations', [])) == 0:
                    error_code = i.get('error', {}).get('code', 0)
                    message = i.get('error', {}).get('message', '')
                    final_report[res][i['name']] = [{'violations': [
                        {'description': f"code: {error_code}. error_message: {message}"} # noqa
                    ]}]
                else:
                    final_report[res][i['name']] = violations   # noqa

    # Org level resources
    org_url = source_ui_url + source_url
    dg.add_node('ORG' + SEPERATOR + source_url, size=30, color='pink')
    dg.nodes['ORG' + SEPERATOR +
            source_url]['title'] = f'<a href={org_url} target="_blank">Organization - {source_url}</a>'  # noqa pylint: disable=C0301
    for key, value in exportorg.items():  # noqa pylint: disable=R1702
        dg.add_edge('ORG' + SEPERATOR + key.upper(),
                    'ORG' + SEPERATOR + source_url)
        dg.nodes['ORG' + SEPERATOR + key.upper()]['size'] = 20

        # for titles of key nodes
        if key == 'apiProducts':
            res_url = source_ui_url + source_url + '/products'
            dg.nodes['ORG' + SEPERATOR + key.upper()
                    ]['title'] = f'<a href={res_url} target="_blank">Org level {key}</a>'  # noqa
        elif key == 'kvms':
            res_url = api_url + '/key-value-maps/1/overview'
            dg.nodes['ORG' + SEPERATOR + key.upper()
                    ]['title'] = f'<a href={res_url} target="_blank">Org level {key}</a>'  # noqa
        else:
            res_url = source_ui_url + source_url + '/' + key
            dg.nodes['ORG' + SEPERATOR + key.upper()
                    ]['title'] = f'<a href={res_url} target="_blank">Org level {key}</a>'  # noqa

        # check threshold for resources
        threshold = 100
        if len(value) > threshold:
            dg.add_edge('More than ' + str(threshold) + ' ' +
                        key, 'ORG' + SEPERATOR + key.upper())
            dg.nodes['More than ' + str(threshold) + ' ' + key]['color'] = 'black'  # noqa
            dg.nodes['More than ' + str(threshold) + ' ' + key]['size'] = 20
            dg.nodes['More than ' + str(threshold) + ' ' +
                    key]['title'] = 'Total - ' + str(len(value)) + ' ' + key  # noqa
            continue

        for name, val in value.items():
            dg.add_edge('ORG' + SEPERATOR + name,
                        'ORG' + SEPERATOR + key.upper())
            if key in ['apis', 'sharedflows']:
                dg.nodes['ORG' + SEPERATOR + name]['title'] = key[:-1] + ' named ' + name   # noqa
            else:
                dg.nodes['ORG' + SEPERATOR + name]['title'] = 'Org level ' + \
                            key[:-1] + ' named ' + name

            # check if importable or not
            if key in ['apis', 'sharedflows']:
                if final_report.get(key):
                    if final_report.get(key, {}).get(name, True) is not True:
                        dg.nodes['ORG' + SEPERATOR + name]['color'] = 'red'
                        count = 1
                        viols = ""
                        each_resource = final_report.get(key, {}).get(name, [{'violations': []}])   # noqa pylint: disable=C0301
                        for violation in each_resource[0].get('violations', []):  # noqa
                            viols += str(count) + ". "
                            if isinstance(violation, dict):
                                viols += violation.get('description', '') + " "
                            else:
                                viols += str(violation) + " "
                            count = count+1
                        dg.nodes['ORG' + SEPERATOR +
                                name]['title'] = '<b>Reason</b> : ' + viols   # noqa

    # Environment level resources
    dg.add_edge('ORG' + SEPERATOR + 'ENVs', 'ORG' + SEPERATOR + source_url)
    dg.nodes['ORG' + SEPERATOR + 'ENVs']['size'] = 20
    env_url = api_url + '/environments/1/overview'
    dg.nodes['ORG' + SEPERATOR +
            'ENVs']['title'] = f'<a href={env_url} target="_blank">Environments</a>'  # noqa

    for env, value in exportenv.items():
        dg.add_edge(env, 'ORG | ENVs')
        dg.nodes[env]['title'] = env + ' Environment'
        base_url = source_ui_url + source_url + '/environments/' + env + '/'   # noqa
        for resource, val in value.items():
            dg.add_edge(env + SEPERATOR + resource.upper(), env)

            # hyperlinks in titles
            if resource == 'resourcefiles':
                res_url = api_url + '/resource-files/1/overview'
                dg.nodes[env + SEPERATOR + resource.upper(
                )]['title'] = f'<a href={res_url} target="_blank">Env {env} level {resource}</a>'  # noqa pylint: disable=C0301
            elif resource == 'kvms':
                res_url = base_url + 'key-value-maps'
                dg.nodes[env + SEPERATOR + resource.upper(
                )]['title'] = f'<a href={res_url} target="_blank">Env {env} level {resource}</a>'  # noqa pylint: disable=C0301
            elif resource == 'vhosts':
                res_url = base_url + 'virtual-hosts'
                dg.nodes[env + SEPERATOR + resource.upper(
                )]['title'] = f'<a href={res_url} target="_blank">Env {env} level {resource}</a>'  # noqa pylint: disable=C0301
            elif resource == 'targetServers':
                res_url = base_url + 'target-servers'
                dg.nodes[env + SEPERATOR + resource.upper(
                )]['title'] = f'<a href={res_url} target="_blank">Env {env} level {resource}</a>'  # noqa pylint: disable=C0301
            else:
                res_url = base_url + resource
                dg.nodes[env + SEPERATOR + resource.upper(
                )]['title'] = f'<a href={res_url} target="_blank">Env {env} level {resource}</a>'  # noqa pylint: disable=C0301

            # check threshold for env level resources
            threshold = 100
            if len(val) > threshold:
                dg.add_edge('More than ' + str(threshold) + ' ' + resource +
                            ' in env ' + env, env + SEPERATOR
                            + resource.upper())
                dg.nodes['More than ' + str(threshold) + ' ' + resource + ' in env ' + env]['color'] = 'black'  # noqa pylint: disable=C0301
                dg.nodes['More than ' + str(threshold) + ' ' + resource + ' in env ' + env]['size'] = 20  # noqa pylint: disable=C0301
                dg.nodes['More than ' + str(threshold) + ' ' + resource + ' in env ' + env]['title'] = 'Total - ' + str(len(val)) + ' ' + resource    # noqa pylint: disable=C0301
                continue

            for name, _ in val.items():
                dg.add_edge(env + SEPERATOR + name, env +
                            SEPERATOR + resource.upper())
                dg.nodes[env + SEPERATOR + name]['title'] = 'Env ' + \
                    env + ' level ' + resource[:-1] + ' named ' + name

                # check if importable or not
                if resource in ['targetServers', 'resourcefiles']:
                    if final_report[env + SEPERATOR + resource][name] is not True: # noqa
                        dg.nodes[env + SEPERATOR + name]['color'] = 'red'
                        error_message = final_report[env + SEPERATOR + resource][name][0].get('error_msg', {}).get('message', '')  # noqa pylint: disable=C0301
                        dg.nodes[env + SEPERATOR + name]['title'] = '<b>Reason</b> : ' +  error_message   # noqa pylint: disable=C0301

    net = Network(notebook=True, cdn_resources='in_line',
                  width=1000, height=800)
    net.from_nx(dg)
    target_dir = cfg.get('inputs', 'TARGET_DIR')
    visualization_graph_file = backend_cfg.get(
        'visualize', 'VISUALIZATION_GRAPH_FILE', fallback='visualization.html')
    net.show(f'{target_dir}/{visualization_graph_file}')


def qualification_report(cfg, backend_cfg, export_data, topology_mapping):
    """Generates a comprehensive qualification report.

    Generates a detailed Excel report summarizing the assessment of
    the Apigee environment for migration. This includes information on
    topology, limitations, potential issues, and recommendations
    for migration.

    Args:
        cfg (configparser.ConfigParser): The parsed configuration from
                                        input.properties.
        backend_cfg (configparser.ConfigParser): The parsed backend
                                                configuration.
        export_data (dict): A dictionary containing the exported
                            artifact data.
        topology_mapping (dict):  A dictionary containing topology
                                mapping information.

    Returns:
        None
    """
    logger.info(
        '------------------- Qualification Report -----------------------')

    target_dir = cfg.get('inputs', 'TARGET_DIR')
    org_name = cfg.get('inputs', 'SOURCE_ORG')
    qualification_report_name = backend_cfg.get(
        'report', 'QUALIFICATION_REPORT', fallback='qualification_report.xlsx')

    qualification_report_obj = QualificationReport(
        f'{target_dir}/{qualification_report_name}',
        export_data,
        topology_mapping,
        cfg,
        backend_cfg,
        org_name
    )

    source_apigee_version = cfg.get('inputs', 'SOURCE_APIGEE_VERSION')

    if not os.environ.get("IGNORE_ENV_SHARD") == "true":
        qualification_report_obj.sharding()

    if source_apigee_version == 'OPDK':
        qualification_report_obj.report_network_topology()

    qualification_report_obj.report_api_with_multiple_basepaths()
    qualification_report_obj.report_env_limits()
    qualification_report_obj.report_org_limits()
    qualification_report_obj.report_api_limits()
    qualification_report_obj.report_unsupported_policies()
    qualification_report_obj.report_cname_anomaly()
    qualification_report_obj.report_json_path_enabled()
    qualification_report_obj.report_apps_without_api_products()
    qualification_report_obj.report_cache_without_expiry()
    qualification_report_obj.report_anti_patterns()
    qualification_report_obj.report_company_and_developer()
    qualification_report_obj.report_north_bound_mtls()
    qualification_report_obj.report_proxies_per_env()
    qualification_report_obj.report_alias_keycert()
    qualification_report_obj.sharded_proxies()
    qualification_report_obj.report_org_resourcefiles()
    qualification_report_obj.report_api_traffic() # NEW: Call the new report method
    qualification_report_obj.validation_report()
    qualification_report_obj.qualification_report_summary()

    qualification_report_obj.reverse_sheets()

    qualification_report_obj.close()


def get_topology(cfg):
    """Determines the topology of the source Apigee OPDK installation.

    Analyzes the source Apigee OPDK installation to determine its
    topology, including the mapping of components to pods and data
    centers.  It generates diagrams visualizing the topology and
    returns a JSON representation of the topology data.

    Args:
        cfg (configparser.ConfigParser): The parsed configuration from
                                        input.properties.

    Returns:
        dict: A dictionary containing the topology data.
    """
    logger.info(
        '------------------- Installation Topology -----------------------')

    source_url = cfg.get('inputs', 'SOURCE_URL')
    source_org = cfg.get('inputs', 'SOURCE_ORG')
    source_auth_token = get_source_auth_token()
    source_auth_type = cfg.get('inputs', 'SOURCE_AUTH_TYPE')
    apigee_topology = ApigeeTopology(
        source_url,
        source_org,
        source_auth_token,
        source_auth_type,
        cfg
    )

    pod_component_mapping = apigee_topology.get_topology_mapping()

    data_center_mapping = apigee_topology.get_data_center_mapping(
        pod_component_mapping)

    apigee_topology.draw_topology_graph_diagram(data_center_mapping)

    topology_json = {
        "pod_component_mapping": pod_component_mapping,
        "data_center_mapping": data_center_mapping
    }
    return topology_json
