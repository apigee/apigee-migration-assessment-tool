#!/usr/bin/python      # noqa pylint: disable=C0302

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

"""Utilities for Apigee proxy analysis and \
manipulation.

This module provides helper functions for \
parsing configurations,
managing files and directories, processing \
proxy artifacts,
and handling parallel execution.
"""
import os
import sys
import csv
import json
import shutil
import hashlib
import configparser
import concurrent.futures
from time import sleep
import zipfile
import requests  # pylint: disable=E0401
import xmltodict  # pylint: disable=E0401
from base_logger import logger, EXEC_INFO


def parse_config(config_file):
    """Parses a configuration file.

    Args:
        config_file: The path to the \
        configuration file.

    Returns:
        A ConfigParser object.
    """
    config = configparser.ConfigParser()
    config.read(config_file)
    if len(config.sections()) == 0:
        logger.error(
        'Unable to read input.properties file.')   # noqa pylint: disable=C0301
        logger.error(
        'Check if input.properties file exists OR if you permissions to view it')   # noqa pylint: disable=C0301
        sys.exit(1)
    return config


def get_env_variable(key):
    """Retrieves the value of an \
    environment variable.

    Args:
        key: The name of the environment \
        variable.

    Returns:
        The value of the environment \
        variable, or None
        if it is not set.
    """
    if key is not None:
        value = os.getenv(key)
        if value is not None:
            return value
    return None


def is_token_valid(token, ssl_verify=True):
    """Checks if an access token is valid.

    Args:
        token: The access token to validate.

    Returns:
        True if the token is valid, \
        False otherwise.
    """
    url = f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={token}"  # noqa
    r = requests.get(url, timeout=5, verify=ssl_verify)
    if r.status_code == 200:
        response_json = r.json()
        if 'email' not in response_json:
            response_json['email'] = ''
        logger.info(f"Token Validated for user {response_json['email']}")  # noqa pylint: disable=W1203
        return True
    return False


def get_access_token(ssl_verify=True):
    """Retrieves the Apigee access token.

    Returns:
        The access token.
    """
    token = os.getenv('APIGEE_ACCESS_TOKEN')
    if token is not None:
        if is_token_valid(token, ssl_verify):
            return token
    logger.error(
        'please run "export APIGEE_ACCESS_TOKEN=$(gcloud auth print-access-token)" first !! ')   # noqa pylint: disable=C0301
    sys.exit(1)


def get_source_auth_token():
    """Retrieves the source auth \
    token.
    Returns:
        The source auth token.
    """
    token = os.getenv('SOURCE_AUTH_TOKEN')
    if token is not None:
        return token
    logger.error(
        "Please run \"export SOURCE_AUTH_TOKEN=`echo -n '<username>:<password>' | base64`\" first!")   # noqa pylint: disable=C0301
    sys.exit(1)


def create_dir(dir_name):
    """Creates a directory if it doesn't \
    exist.

    Args:
        dir: The directory path to create.
    """
    try:
        os.makedirs(dir_name)
    except FileExistsError:
        logger.info(f"Directory \"{dir_name}\" already exists", exc_info=EXEC_INFO)  # noqa pylint: disable=W1203


def list_dir(dir_name, isok=False):  # noqa pylint: disable=R1710
    """Lists the contents of a directory.

    Args:
        dir: The directory path to list.
        isok: Whether to ignore \
        FileNotFoundError.

    Returns:
        A list of directory contents.
    """
    try:
        return os.listdir(dir_name)
    except FileNotFoundError as error:
        logger.warning(f"{error}")  # noqa pylint: disable=W1203
        if isok:
            logger.info(f"Ignoring : Directory \"{dir_name}\" not found")  # noqa pylint: disable=W1203
            return []
        logger.error(f"Directory \"{dir_name}\" not found", exc_info=EXEC_INFO)  # noqa pylint: disable=W1203
        # fix abrupt exit
        # sys.exit(1)


def delete_folder(src):
    """Deletes a folder.

    Args:
        src: Path to the folder.
    """
    try:
        shutil.rmtree(src)
    except FileNotFoundError as e:
        logger.info(f'Ignoring : {e}')  # noqa pylint: disable=W1203


def print_json(data):
    """Prints JSON data.

    Args:
        data: data to print
    """
    logger.info(json.dumps(data, indent=2))


def parse_json(file):
    """Parses JSON data from a file.

    Args:
        file: Path to file

    Returns:
        Parsed JSON data
    """
    try:
        with open(file) as fl:  # noqa pylint: disable=W1514
            doc = json.loads(fl.read())
        return doc
    except FileNotFoundError:
        logger.warning(f"File \"{file}\" not found", exc_info=EXEC_INFO)  # noqa pylint: disable=W1203
    return {}


def write_json(file, data):
    """Writes JSON data to a file.

    Args:
        file: The file path to write to.
        data: The JSON data to write.

    Returns:
        True if successful, False \
        otherwise.
    """
    try:
        logger.info(f"Writing JSON to File {file}")  # noqa pylint: disable=W1203
        with open(file, 'w') as fl:  # noqa pylint: disable=W1514
            fl.write(json.dumps(data, indent=2))
    except FileNotFoundError:
        logger.error(f"File \"{file}\" not found", exc_info=EXEC_INFO)  # noqa pylint: disable=W1203
        return False
    return True


def read_file(file_path):
    """Reads data from a file.

    Args:
        file_path (str): The path to the file.

    Returns:
        bytes: The content of the file.
    """
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        return content
    except Exception as e: # noqa pylint: disable=W1203,W0718
        logger.error(f"Couldn't read file {file_path}. ERROR-INFO- {e}")  # noqa pylint: disable=W1203
        return None


def write_file(file_path, data):
    """Writes data to a file.

    Args:
        file_path (str): The path to the file.
        data (bytes): The data to write.
    """
    try:
        with open(file_path, "wb") as f:
            f.write(data)
    except Exception as e: # noqa pylint: disable=W1203,W0718
        logger.error(f"Couldn't read file {file_path}. ERROR-INFO- {e}")  # noqa pylint: disable=W1203


def compare_hash(data1, data2):
    """Compares the SHA256 hash of two \
    data objects.

    Args:
        data1: The first data object.
        data2: The second data object.

    Returns:
        True if the hashes match, \
        False otherwise.
    """
    try:
        data1_hash = hashlib.sha256(data1).hexdigest()
        data2_hash = hashlib.sha256(data2).hexdigest()
        return bool(data1_hash == data2_hash)
    except Exception as e: # noqa pylint: disable=W1203,W0718
        logger.error(f"Hashes couldn't be matched. ERROR-INFO- {e}")  # noqa pylint: disable=W1203
        return False


def get_proxy_endpoint_count(cfg):
    """Retrieves the proxy endpoint count \
    from

        configuration.

    Args:
        cfg: The configuration object.

    Returns:
        The proxy endpoint count.
    """
    try:
        proxy_endpoint_count = cfg.getint('unifier', 'proxy_endpoint_count')
        max_proxy_endpoint_count = cfg.getint(
            'inputs', 'MAX_PROXY_ENDPOINT_LIMIT')
        if proxy_endpoint_count < 0:
            logger.error(
                    'ERROR: Proxy Endpoints should be > Zero(0)')
            sys.exit(1)
        if proxy_endpoint_count > max_proxy_endpoint_count:
            logger.error(
                    'ERROR: Proxy Endpoints should be > Zero(0)  &  <= %s',
                    max_proxy_endpoint_count)
            sys.exit(1)
    except ValueError:
        logger.error('proxy_endpoint_count should be a Number')
        sys.exit(1)
    return proxy_endpoint_count


def generate_env_groups_tfvars(project_id, env_config):
    """Generates Terraform variables for \
    environment groups.

    Args:
        project_id: The GCP project ID.
        env_config: The environment \
        configuration.

    Returns:
        A dictionary of Terraform variables.
    """
    envgroups = {}
    environments = {}
    for env, env_data in env_config.items():
        environments[env] = {
            'display_name': env,
            'description': f"Apis for environment {env}",
        }
        environments[env]['envgroups'] = []
        for vhost, vhosts_data in env_data['vhosts'].items():
            env_group_name = f"{env}-{vhost}"
            environments[env]['envgroups'].append(env_group_name)
            envgroups[env_group_name] = vhosts_data['hostAliases']
    tfvars = {
        'project_id': project_id,
        'envgroups': envgroups,
        'environments': environments
    }
    return tfvars


def write_csv_report(file_name, header, rows):
    """Writes data to a CSV file.

    Args:
        file_name: The name of the CSV file.
        header: The header row.
        rows: The data rows.
    """
    with open(file_name, 'w', newline='') as file:  # noqa pylint: disable=W1514
        writer = csv.writer(file)
        writer.writerow(header)
        for each_row in rows:
            writer.writerow(each_row)


def retry(retries=3, delay=1, backoff=2):  # noqa pylint: disable=W0613
    """Retry decorator with exponential \
    backoff.

    Args:
        retries: Number of retries
        delay: Initial delay
        backoff: Backoff multiplier

    Returns:
        Decorated function
    """
    def decorator(func):   # noqa
        def wrapper(*args, **kwargs): # noqa pylint: disable=R1710
            delay = 1
            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e: # noqa pylint: disable=W1203,W0718
                    if attempt == retries:
                        raise e
                    logger.info(f"Retrying {func.__name__} in {delay} seconds... (Attempt {attempt + 1})")   # noqa pylint: disable=C0301,W1203
                    sleep(delay)
                    delay *= backoff   # noqa
        return wrapper
    return decorator


def run_parallel(func, args, workers=10,
                 max_retries=3, retry_delay=1):
    """Runs a function in parallel with \
    multiple arguments.

    Args:
        func: Function to execute.
        args: Arguments for the function.
        workers: Number of workers.
        max_retries: Max retry attempts.
        retry_delay: Retry delay.

    Returns:
        List of results.
    """
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:  # noqa
        # Initial futures (future: (arg, retry_count))
        future_to_arg_retry = {executor.submit(func, arg): (arg, 0) for arg in args}  # noqa

        data = []
        while future_to_arg_retry:
            done, _ = concurrent.futures.wait(future_to_arg_retry, return_when=concurrent.futures.FIRST_COMPLETED)   # noqa pylint: disable=C0301
            for future in done:
                arg, retry_count = future_to_arg_retry.pop(future)
                try:
                    data.append(future.result())
                except Exception as exc:   # noqa pylint: disable=W1203,W0718
                    if retry_count < max_retries:
                        retry_count += 1
                        logger.warning(  # noqa pylint: disable=W1203
                            f"Task with arg {arg} failed ({retry_count}/{max_retries} retries), retrying in {retry_delay} seconds...",   # noqa pylint: disable=C0301,W1203
                            exc_info=True,
                        )
                        sleep(retry_delay)
                        future_to_arg_retry[executor.submit(func, arg)] = (arg, retry_count)   # noqa pylint: disable=C0301
                    else:
                        data.append("Exception")
                        logger.error(  # noqa pylint: disable=W1203
                            f"Task with arg {arg} failed with {exc} after {max_retries} retries.",   # noqa pylint: disable=C0301
                            exc_info=True
                        )
    return data


def get_proxy_entrypoint(dir_name):
    """Gets the proxy entrypoint XML file.


    Args:
        dir: Proxy directory.

    Returns:
        Path to the entrypoint XML file.
    """
    try:
        files = list_dir(dir_name)
        ent = []

        for eachfile in files:
            if eachfile.endswith(".xml"):

                ent.append(eachfile)
        if len(ent) == 1:
            return os.path.join(dir_name, ent[0])
        if len(ent) > 1:
            logger.error(  # noqa pylint: disable=W1203
                f"ERROR: Directory \"{dir_name}\" contains multiple xml files at root")  # noqa
        else:
            logger.error(  # noqa pylint: disable=W1203
                f"ERROR: Directory \"{dir_name}\" has no xml file at root")
    except Exception as error: # noqa pylint: disable=W1203,W0718
        logger.info(f"INFO: get proxy endpoint module faced a {error}")  # noqa pylint: disable=W1203
    if len(ent) == 1:
        return os.path.join(dir_name, ent[0])
    return None


def parse_xml(file):
    """Parses XML data from a file.


    Args:
        file: Path to XML file.

    Returns:
        Parsed XML data as a dictionary.
    """
    try:
        with open(file) as fl:  # noqa pylint: disable=W1514
            doc = xmltodict.parse(fl.read())
        return doc
    except FileNotFoundError:
        logger.error(f"File \"{file}\" not found", exc_info=EXEC_INFO)  # noqa pylint: disable=W1203
    return {}


def get_proxy_files(dir_name, file_type='proxies'):
    """Gets proxy files of a specific type.


    Args:
        dir_name: Proxy directory.
        file_type: Type of proxy files.

    Returns:
        List of proxy file names \
        without extension.
    """
    target_dir = os.path.join(dir_name, file_type)
    files = list_dir(target_dir)
    xml_files = []
    for eachfile in files:
        if eachfile.endswith(".xml"):
            xml_files.append(os.path.splitext(eachfile)[0])
    if len(xml_files) == 0:
        logger.error(f"ERROR: Directory \"{target_dir}\" has no xml files")   # noqa pylint: disable=W1203
        return []
    return xml_files


def parse_proxy_root(dir_name):
    """Parses the root XML of Apigee proxy.


    Args:
        dir_name: The directory containing \
        the proxy files.

    Returns:
        A dictionary representing the parsed XML.
    """
    try:
        file = get_proxy_entrypoint(dir_name)
        if file is None:
            return {}
        doc = parse_xml(file)
        api_proxy = doc.get('APIProxy', {})
        proxy_endpoints = api_proxy.get('ProxyEndpoints', {}).get('ProxyEndpoint', {})  # noqa
        target_endpoints = api_proxy.get('TargetEndpoints', {}).get('TargetEndpoint', {})  # noqa
        policies = api_proxy.get('Policies', {}).get('Policy', {})
        if len(proxy_endpoints) == 0:
            logger.info('Proceeding with Filesystem parse of ProxyEndpoints')
            doc['APIProxy']['ProxyEndpoints'] = {}
            proxies = get_proxy_files(dir_name)
            doc['APIProxy']['ProxyEndpoints']['ProxyEndpoint'] = proxies
        else:
            logger.info('Skipping with Filesystem parse of ProxyEndpoints')
        if len(target_endpoints) == 0:
            logger.info('Proceeding with Filesystem parse of TargetEndpoints')
            doc['APIProxy']['TargetEndpoints'] = {}
            targets = get_proxy_files(dir_name, 'targets')
            doc['APIProxy']['TargetEndpoints']['TargetEndpoint'] = targets
        else:
            logger.info('Skipping with Filesystem parse of TargetEndpoints')
        if len(policies) == 0:
            logger.info('Proceeding with Filesystem parse of Policies')
            doc['APIProxy']['Policies'] = {}
            policies_list = get_proxy_files(dir_name, 'policies')
            doc['APIProxy']['Policies']['Policy'] = policies_list
        else:
            logger.info('Skipping with Filesystem parse of Policies')
    except Exception as error: # noqa pylint: disable=W1203,W0718
        logger.error(f"raised in parse_proxy_root {error}")  # noqa pylint: disable=W1203
    return doc


def parse_proxy_root_sharding(dir_name):
    """Parses the root XML of Apigee \
    proxy for sharding.

    Args:
        dir_name: The directory containing \
        the proxy files.

    Returns:
        A dictionary representing the \
        parsed XML.
    """
    file = get_proxy_entrypoint(dir_name)
    if file is None:
        return {}
    doc = parse_xml(file)
    return doc


def read_proxy_artifacts(dir_name, entrypoint):
    """Reads Apigee proxy artifacts \
    from a directory.

    Args:
        dir: The directory containing \
        the proxy files.
        entrypoint: The entrypoint \
        configuration.

    Returns:
        A dictionary containing the \
        parsed proxy artifacts.
    """
    try:
        api_proxy = entrypoint['APIProxy']

        proxy_name = entrypoint['APIProxy']['@name']
        proxy_dict = {
            'BasePaths': [],
            'Policies': {},
            'ProxyEndpoints': {},
            'TargetEndpoints': {},
            'proxyName': proxy_name
        }

        proxy_endpoints = api_proxy.get('ProxyEndpoints')
        if proxy_endpoints is not None:
            proxy_endpoints = api_proxy['ProxyEndpoints'].get('ProxyEndpoint')

            proxy_endpoints = ([proxy_endpoints] if isinstance(
                proxy_endpoints, str) else proxy_endpoints)
            for each_pe in proxy_endpoints:
                proxy_dict['ProxyEndpoints'][each_pe] = parse_xml(
                    os.path.join(dir_name, 'proxies', f"{each_pe}.xml"))

            if api_proxy.get('Basepaths', None) is not None:
                proxy_dict['BasePaths'] = api_proxy.get('Basepaths')
            if api_proxy.get('BasePaths', None) is not None:
                proxy_dict['BasePaths'] = api_proxy.get('BasePaths')

        if api_proxy.get('Policies') is not None:
            policies = api_proxy['Policies']['Policy']
            policies = ([policies] if isinstance(
                api_proxy['Policies']['Policy'], str) else policies)

            for each_policy in policies:
                proxy_dict['Policies'][each_policy] = parse_xml(
                    os.path.join(dir_name, 'policies', f"{each_policy}.xml"))

        if api_proxy.get('TargetEndpoints') is not None:

            target_endpoints = api_proxy['TargetEndpoints']['TargetEndpoint']
            target_endpoints = ([target_endpoints] if isinstance(
                target_endpoints, str) else target_endpoints)
            for each_te in target_endpoints:
                proxy_dict['TargetEndpoints'][each_te] = parse_xml(
                    os.path.join(dir_name, 'targets', f"{each_te}.xml"))
    except Exception as error: # noqa pylint: disable=W1203,W0718
        logger.error(f"Error: raised error in read_proxy_artifacts {error}")  # noqa pylint: disable=W1203
    return proxy_dict


def get_target_endpoints(proxy_endpoint_data):
    """Retrieves target endpoints from \
    proxy endpoint data.

    Args:
        ProxyEndpointData: Proxy endpoint \
        data dictionary.

    Returns:
        A list of target endpoints.
    """
    target_endpoints = []
    routes = proxy_endpoint_data.get('RouteRule', [])
    if len(routes) > 0:
        routes = (
            [proxy_endpoint_data['RouteRule']]
            if isinstance(proxy_endpoint_data['RouteRule'], dict)
            else proxy_endpoint_data['RouteRule']
        )

    for each_route in routes:
        if 'TargetEndpoint' in each_route:
            target_endpoints.append(each_route['TargetEndpoint'])
    return target_endpoints


def get_all_policies_from_step(step):
    """Retrieves all policies from a step.

    Args:
        Step: Step data dictionary.

    Returns:
        A list of policy names.
    """

    policies = []
    step_data = ([step] if isinstance(step, dict) else step)
    for each_step in step_data:
        policies.append(each_step['Name'])
    return policies


def get_all_policies_from_flow(flow, fault_rule=False):  # noqa pylint: disable=R0912
    """Retrieves all policies from a flow.

    Args:
        Flow: Flow data dictionary.
        fault_rule: Boolean indicating \
        whether to
            process fault rules.

    Returns:
        A list of policy names.
    """
    policies = []

    if not fault_rule:
        if flow.get('Request'):
            if isinstance(flow['Request'], list) and len(flow['Request']) > 0:
                flow['Request'] = flow['Request'][0]
            request = ([] if flow['Request'] is None else (
                        [] if flow['Request'].get('Step') is None else
                        (
                            [flow['Request']['Step']] if isinstance(flow['Request']['Step'], dict)    # noqa pylint: disable=C0301
                            else flow['Request']['Step']
                        )))
        else:
            request = []
        if flow.get('Response'):
            if (isinstance(flow['Response'], list) and
                    len(flow['Response']) > 0):
                flow['Response'] = flow['Response'][0]
            response = ([] if flow['Response'] is None else (
                            [] if flow['Response'].get('Step') is None else
                            (
                            [flow['Response']['Step']] if isinstance(flow['Response']['Step'], dict)   # noqa pylint: disable=C0301
                                else flow['Response']['Step']
                            )))
        else:
            response = []
        for each_flow in request:
            policies.extend(get_all_policies_from_step(each_flow))
        for each_flow in response:
            policies.extend(get_all_policies_from_step(each_flow))
    else:
        if flow is None:
            fault_rules = []
        elif flow.get('FaultRule', None) is None:
            fault_rules = []
        else:
            fault_rules = (
                [flow.get('Step')] if isinstance(flow['FaultRule'].get('Step'), dict)  # noqa
                else flow['FaultRule'].get('Step')
            )
        for each_step in fault_rules:
            policies.extend(get_all_policies_from_step(each_step))
    return policies


def get_all_policies_from_endpoint(endpoint_data, endpoint_type):
    """Retrieves all policies from \
    an endpoint.

    Args:
        endpointData: Endpoint data \
        dictionary.
        endpointType: Type of endpoint \
        ('ProxyEndpoint'
            or 'TargetEndpoint').

    Returns:
        A list of policy names.
    """
    policies = []
    policies.extend(
        get_all_policies_from_flow(
            endpoint_data[endpoint_type]['PreFlow']
        ) if endpoint_data[endpoint_type].get('PreFlow') else []
    )
    policies.extend(
        get_all_policies_from_flow(
            endpoint_data[endpoint_type]['PostFlow']
        ) if endpoint_data[endpoint_type].get('PostFlow') else []
    )

    if (isinstance(endpoint_data[endpoint_type].get('Flows'), list) and
            len(endpoint_data[endpoint_type].get('Flows')) > 0):
        endpoint_data[endpoint_type]['Flows'] = endpoint_data[endpoint_type]['Flows'][0]  # noqa

    flows = (
        []
        if endpoint_data[endpoint_type].get('Flows') is None else
        ([] if endpoint_data[endpoint_type].get('Flows').get('Flow') is None
            else (
                [endpoint_data[endpoint_type]['Flows']['Flow']]
                if isinstance(
                    endpoint_data[endpoint_type]['Flows']['Flow'], dict)
                else
                endpoint_data[endpoint_type]['Flows']['Flow']
            )))

    for each_flow in flows:
        if isinstance(each_flow, dict):
            policies.extend(
                get_all_policies_from_flow(
                    each_flow
                )
            )
    if 'DefaultFaultRule' in endpoint_data[endpoint_type]:

        policies.extend(
            get_all_policies_from_flow(
                endpoint_data[endpoint_type]['DefaultFaultRule'], True)
        )

    return policies


def get_proxy_objects_relationships(proxy_dict):
    """Gets relationships between proxy objects.

    Args:
        proxy_dict: Dictionary containing \
        proxy data.

    Returns:
        Dictionary mapping proxy endpoints \
        to their
        policies, basepaths, and target endpoints.
    """
    proxy_object_map = {}
    proxy_endpoints = proxy_dict['ProxyEndpoints']
    for proxy_endpoint, proxy_endpoint_data in proxy_endpoints.items():
        proxy_object_map[proxy_endpoint] = {}

        target_endpoints = get_target_endpoints(
            proxy_endpoint_data['ProxyEndpoint'])
        target_endpoints_data = {
            te: proxy_dict['TargetEndpoints'][te] for te in target_endpoints}
        policies = []
        policies.extend(get_all_policies_from_endpoint(
            proxy_endpoint_data, 'ProxyEndpoint'))
        for _, each_te in target_endpoints_data.items():
            policies.extend(get_all_policies_from_endpoint(
                each_te, 'TargetEndpoint'))
        proxy_object_map[proxy_endpoint] = {
            'Policies': policies,
            'BasePath': proxy_endpoint_data['ProxyEndpoint']['HTTPProxyConnection'].get('BasePath'),   # noqa pylint: disable=C0301
            'TargetEndpoints': target_endpoints,
        }

    return proxy_object_map


def get_api_path_groups(each_api_info):
    """Groups API paths based on their \
    base path.

    Args:
        each_api_info: Dictionary \
        containing API
            information.

    Returns:
        Dictionary mapping base paths to \
        lists of
        proxy endpoints.
    """
    api_path_group_map = {}
    for pe, pe_info in each_api_info.items():
        if pe_info['BasePath'] is None:
            if '_null_' in api_path_group_map:
                api_path_group_map['_null_'].append({pe: None})
            else:
                api_path_group_map['_null_'] = [{pe: None}]
        else:
            base_path_split = [i for i in pe_info['BasePath'].split('/') if i != ""]  # noqa
            if base_path_split[0] in api_path_group_map:
                api_path_group_map[base_path_split[0]].append(
                    {pe: base_path_split[0]})
            else:
                api_path_group_map[base_path_split[0]] = [{pe: base_path_split[0]}]  # noqa
    return api_path_group_map


def group_paths_by_path(api_info, pe_count_limit):
    """Groups API paths based on a count limit.

    Args:
        api_info (dict): Dictionary of API path data.
        pe_count_limit (int): The maximum number of paths per group.

    Returns:
        list: A list of groups, where each group is a list of API paths.
    """
    result = []
    paths = list(api_info.keys())
    path_count = len(paths)
    if path_count > pe_count_limit:
        for i in range(0, path_count, pe_count_limit):
            each_result = []
            if i+pe_count_limit > path_count:
                for k in paths[i:path_count]:
                    each_result.extend(api_info[k])
            else:
                for k in paths[i:i+pe_count_limit]:
                    each_result.extend(api_info[k])
            result.append(each_result)
    else:
        each_result = []
        for _, v in api_info.items():
            each_result.extend(v)
        result.append(each_result)
    return result


def bundle_path(each_group_bundle):
    """Bundles API paths within each group.


    Args:
        each_group_bundle: List of API path groups.

    Returns:
        List of bundled API paths.
    """
    outer_group = []
    for each_group in each_group_bundle:
        subgroups = {}
        for each_pe in each_group:
            path = list(each_pe.values())[0]
            proxy_ep = list(each_pe.keys())[0]
            if path in subgroups:
                subgroups[path].append(proxy_ep)
            else:
                subgroups[path] = [proxy_ep]
        outer_group.append(subgroups)
    return outer_group


def process_steps(step, condition):
    """Processes steps in a flow.


    Args:
        step (dict): The step data.
        condition (str): The condition to apply.

    Returns:
        list: A list of processed steps.
    """
    processed_step = []
    if step is None:
        return processed_step
    if isinstance(step['Step'], dict):
        processed_step = [apply_condition(step['Step'], condition)]
    if isinstance(step['Step'], list):
        processed_step = [apply_condition(i, condition) for i in step['Step']]
    return processed_step


def process_flow(flow, condition):
    """Processes flows with conditions.


    Args:
        flow (dict): flow dictionary
        condition (str): condition string

    Returns:
        dict: processed flow dictionary.
    """
    processed_flow = flow.copy()
    if flow['Request'] is not None:
        processed_flow['Request']['Step'] = process_steps(flow['Request'],
                                                          condition)
    if flow['Response'] is not None:
        processed_flow['Response']['Step'] = process_steps(flow['Response'],
                                                           condition)
    processed_flow_with_condition = apply_condition(processed_flow,
                                                    condition)
    return processed_flow_with_condition


def process_route_rules(route_rules, condition):
    """Processes route rules with \
    conditions.

    Args:
        route_rules: The route rules data.
        condition: The condition to apply.

    Returns:
        A list of processed route rules.
    """
    processed_rr = []
    for each_rr in (route_rules if isinstance(route_rules, list)
                    else [route_rules]):
        each_processed_rr = apply_condition(each_rr, condition)
        processed_rr.append(each_processed_rr)
    return processed_rr


def apply_condition(step, condition):
    """Applies a condition to a step \
    or rule.

    Args:
        step: The step or rule data.
        condition: The condition to apply.

    Returns:
        The modified step or rule data.
    """
    step_or_rule = step.copy()
    if 'Condition' in step_or_rule:
        if step_or_rule['Condition'] is None:
            step_or_rule['Condition'] = condition
        elif len(step_or_rule['Condition'].strip()) > 0:
            if step_or_rule['Condition'].strip().startswith('('):
                step_or_rule['Condition'] = f"{condition} and {step_or_rule['Condition']}"  # noqa
            else:
                step_or_rule['Condition'] = f"{condition} and {step_or_rule['Condition']}"  # noqa
        else:
            step_or_rule['Condition'] = condition
    else:
        step_or_rule['Condition'] = condition
    return step_or_rule


def merge_proxy_endpoints(api_dict, basepath, pes):
    """Merges multiple proxy endpoints \
    into one.

    Args:
        api_dict (dict): The API \
        dictionary.
        basepath (str): The base path \
        for the merged
            endpoint.
        pes (list): List of proxy \
        endpoints to merge.

    Returns:
        dict: The merged proxy endpoint.
    """
    merged_pe = {'ProxyEndpoint': {}}
    for each_pe, each_pe_info in api_dict['ProxyEndpoints'].items():
        if each_pe in pes:
            original_basepath = each_pe_info['ProxyEndpoint']['HTTPProxyConnection']['BasePath']   # noqa pylint: disable=C0301
            # TODO : Build full Request path   # noqa pylint: disable=W0511
            condition = (original_basepath if original_basepath is None else f'(request.path Matches "{original_basepath}*")')   # noqa pylint: disable=C0301
            copied_flows = (
                None if each_pe_info['ProxyEndpoint']['Flows'] is None else each_pe_info['ProxyEndpoint']['Flows'].copy()   # noqa pylint: disable=C0301
            )
            original_flows = ([] if copied_flows is None else
                              ([copied_flows['Flow']] if isinstance(copied_flows['Flow'], dict) else copied_flows['Flow']))   # noqa pylint: disable=C0301

            if len(merged_pe['ProxyEndpoint']) == 0:
                merged_pe['ProxyEndpoint'] = {
                    '@name': [],
                    'Description': None,
                    'FaultRules': None,
                    'PreFlow': {
                        '@name': 'PreFlow',
                        'Request': {'Step': []},
                        'Response': {'Step': []},
                    },
                    'PostFlow': {
                        '@name': 'PostFlow',
                        'Request': {'Step': []},
                        'Response': {'Step': []},
                    },
                    'Flows': {'Flow': []},
                    'HTTPProxyConnection': {'BasePath': '',
                                            'Properties': {},
                                            'VirtualHost': ''},
                    'RouteRule': []
                }

                merged_pe['ProxyEndpoint']['Description'] = each_pe_info['ProxyEndpoint']['Description']   # noqa pylint: disable=C0301
                merged_pe['ProxyEndpoint']['FaultRules'] = each_pe_info['ProxyEndpoint']['FaultRules']   # noqa pylint: disable=C0301
                merged_pe['ProxyEndpoint']['HTTPProxyConnection']['BasePath'] = (basepath if basepath is None else f'/{basepath}')   # noqa pylint: disable=C0301
                merged_pe['ProxyEndpoint']['HTTPProxyConnection']['Properties'] = each_pe_info['ProxyEndpoint']['HTTPProxyConnection']['Properties']   # noqa pylint: disable=C0301
                merged_pe['ProxyEndpoint']['HTTPProxyConnection']['VirtualHost'] = each_pe_info['ProxyEndpoint']['HTTPProxyConnection']['VirtualHost']   # noqa pylint: disable=C0301

            merged_pe['ProxyEndpoint']['@name'].append(each_pe_info['ProxyEndpoint']['@name'])   # noqa pylint: disable=C0301
            merged_pe['ProxyEndpoint']['RouteRule'].extend(
                    process_route_rules(each_pe_info['ProxyEndpoint']['RouteRule'], condition)   # noqa pylint: disable=C0301
            )
            merged_pe['ProxyEndpoint']['PreFlow']['Request']['Step'].extend(
                process_steps(each_pe_info['ProxyEndpoint']['PreFlow']['Request'], condition)   # noqa pylint: disable=C0301
            )
            merged_pe['ProxyEndpoint']['PreFlow']['Response']['Step'].extend(
                process_steps(each_pe_info['ProxyEndpoint']['PreFlow']['Response'], condition)   # noqa pylint: disable=C0301
            )
            merged_pe['ProxyEndpoint']['PostFlow']['Request']['Step'].extend(
                process_steps(each_pe_info['ProxyEndpoint']['PostFlow']['Request'], condition)   # noqa pylint: disable=C0301
            )
            merged_pe['ProxyEndpoint']['PostFlow']['Response']['Step'].extend(
                process_steps(each_pe_info['ProxyEndpoint']['PostFlow']['Response'], condition)   # noqa pylint: disable=C0301
            )
            if 'PostClientFlow' in each_pe_info['ProxyEndpoint']:
                merged_pe['ProxyEndpoint']['PostClientFlow'] = {
                    '@name': 'PostClientFlow',
                    'Request': {'Step': []},
                    'Response': {'Step': []},
                }
                merged_pe['ProxyEndpoint']['PostClientFlow']['Response']['Step'].extend(  # noqa
                    process_steps(each_pe_info['ProxyEndpoint']['PostClientFlow']['Response'], None)   # noqa pylint: disable=C0301
                )
            for each_flow in original_flows:
                merged_pe['ProxyEndpoint']['Flows']['Flow'].append(
                    process_flow(each_flow, condition)
                )
    merged_pe['ProxyEndpoint']['@name'] = "-".join(merged_pe['ProxyEndpoint']['@name'])  # noqa
    return merged_pe


def export_debug_log(files, log_path='logs'):
    """Exports debug logs to JSON files.

    Args:
        files (dict): Dictionary of \
        filenames and data.
        log_path (str): Path to the log \
        directory.
    """
    create_dir(log_path)
    for file, data in files.items():
        file_name = f'{log_path}/{file}.json'
        write_json(file_name, data)


def delete_file(src):
    """Deletes a file.

    Args:
        src (str): Path to the file.
    """
    try:
        os.remove(src)
    except FileNotFoundError as e:
        logger.info(f'Ignoring : {e}')  # noqa pylint: disable=W1203


def write_xml_from_dict(file, data):
    """Writes XML data to a file from \
    a dictionary.

    Args:
        file (str): Path to the file.
        data (dict): Data to write.

    Returns:
        bool: True if successful, \
        False otherwise.
    """
    try:
        with open(file, 'w') as fl:  # noqa pylint: disable=W1514
            fl.write(xmltodict.unparse(data, pretty=True))
    except FileNotFoundError:
        logger.error(f"ERROR: File \"{file}\" not found")  # noqa pylint: disable=W1203
        return False
    return True


def copy_folder(src, dst):
    """Copies a folder.

    Args:
        src (str): Source folder path.
        dst (str): Destination folder \
        path.
    """
    try:
        shutil.copytree(src, dst)
    except FileNotFoundError as e:
        logger.error(e)
        sys.exit(1)


def clean_up_artifacts(target_dir, artifacts_to_retains):
    """Cleans up artifacts in a directory, \
    retaining specified ones.

    Args:
        target_dir (str): The directory \
        to clean.
        artifacts_to_retains (list): \
        Artifacts to retain.
    """
    for file in list_dir(target_dir, True):
        each_policy_file = file.split('.xml')[0]
        if each_policy_file not in artifacts_to_retains:
            delete_file(f"{target_dir}/{file}")


def filter_objects(obj_data, obj_type, targets):
    """Filters objects based on type \
    and target list.

    Args:
        obj_data (dict): The object data.
        obj_type (str): The object type.
        targets (list): The target list.

    Returns:
        dict or None: Filtered object \
        data, or None
            if no matching objects are found.
    """
    result = None
    if obj_data is None:
        return result
    if isinstance(obj_data.get(obj_type), str):
        result = ({obj_type: obj_data[obj_type]} if obj_data[obj_type] in targets else None) # noqa
    elif isinstance(obj_data.get(obj_type), list):
        result = {obj_type: [v for v in obj_data[obj_type] if v in targets]}
    return result


def zipdir(path, ziph):
    """Zips a directory.

    Args:
        path (str): Path to the \
        directory.
        ziph (zipfile.ZipFile): Zip file \
        handle.
    """
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):  # noqa pylint: disable=W0612
        for file in files:
            ziph.write(os.path.join(root, file),
                       os.path.relpath(os.path.join(root, file),
                                       os.path.join(path, '..')))


def clone_proxies(source_dir, target_dir,
                  objects, merged_pes, proxy_bundle_directory):
    """Clones and modifies Apigee proxies.

    Args:
        source_dir (str): The source \
        directory.
        target_dir (str): The target \
        directory.
        objects (dict): Objects to include.
        merged_pes (dict): Merged proxy \
        endpoints.
        proxy_bundle_directory (str): \
        Directory to store
            proxy bundles.

    Returns:
        dict: The merged proxy endpoints.
    """
    try:
        target_dir = f"{target_dir}/apiproxy"
        delete_folder(target_dir)
        copy_folder(source_dir, target_dir)
        file = get_proxy_entrypoint(target_dir)
        # root = parse_xml(file)
        root = parse_proxy_root(target_dir)
        delete_file(file)
        root['APIProxy']['@name'] = objects['Name']
        root['APIProxy']['Policies'] = filter_objects(
            root['APIProxy']['Policies'], 'Policy', objects['Policies'])
        root['APIProxy']['TargetEndpoints'] = filter_objects(
            root['APIProxy']['TargetEndpoints'], 'TargetEndpoint', objects['TargetEndpoints'])   # noqa pylint: disable=C0301
        clean_up_artifacts(f"{target_dir}/policies", objects['Policies'])
        clean_up_artifacts(f"{target_dir}/targets", objects['TargetEndpoints'])
        for pe in objects['ProxyEndpoints']:
            write_xml_from_dict(
                f"{target_dir}/proxies/{pe}.xml", merged_pes[pe])
        clean_up_artifacts(f"{target_dir}/proxies", objects['ProxyEndpoints'])
        root['APIProxy']['ProxyEndpoints'] = {'ProxyEndpoint': (
            objects['ProxyEndpoints'] if len(objects['ProxyEndpoints']) > 1 else objects['ProxyEndpoints'][0])}   # noqa pylint: disable=C0301
        transformed_file = file.split('/')
        transformed_file[-1] = f"{objects['Name']}.xml"
        write_xml_from_dict("/".join(transformed_file), root)
        delete_folder(f"{target_dir}/manifests")

        with zipfile.ZipFile(f"{proxy_bundle_directory}/{objects['Name']}.zip", 'w', zipfile.ZIP_DEFLATED) as zipf:   # noqa pylint: disable=C0301
            zipdir(target_dir, zipf)

    except Exception as error: # noqa pylint: disable=W1203,W0718
        logger.error(   # noqa pylint: disable=C0301,W1203
            f"some error occurred in clone proxy function error. ERROR-INFO - {error}")  # noqa
    return merged_pes
