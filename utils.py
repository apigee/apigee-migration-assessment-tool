#!/usr/bin/python

# Copyright 2023 Google LLC
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

import os
import sys
import csv
import json
import shutil
import zipfile
import requests
import xmltodict
import hashlib
import configparser
import concurrent.futures
from time import sleep
from base_logger import logger, EXEC_INFO


def parse_config(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config


def get_env_variable(key):
    if key is not None:
        value = os.getenv(key)
        if value is not None:
            return value
        else:
            return None


def is_token_valid(token):
    url = f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={token}"
    r = requests.get(url)
    if r.status_code == 200:
        if 'email' not in r.json():
            r.json()['email'] = ''
        logger.info(f"Token Validated for user {r.json()['email']}")
        return True
    return False


def get_access_token():
    token = os.getenv('APIGEE_ACCESS_TOKEN')
    if token is not None:
        if is_token_valid(token):
            return token
    logger.error(
        'please run "export APIGEE_ACCESS_TOKEN=$(gcloud auth print-access-token)" first !! ')
    sys.exit(1)


def get_source_auth_token():
    token = os.getenv('SOURCE_AUTH_TOKEN')
    if token is not None:
        return token
    logger.error(
        "Please run \"export SOURCE_AUTH_TOKEN=`echo -n '<username>:<password>' | base64`\" first!")
    sys.exit(1)


def create_dir(dir):
    try:
        os.makedirs(dir)
    except FileExistsError:
        logger.info(f"Directory \"{dir}\" already exists", exc_info=EXEC_INFO)


def list_dir(dir, isok=False):
    try:
        return os.listdir(dir)
    except FileNotFoundError as error:
        logger.warn(f"{error}")
        if isok:
            logger.info(f"Ignoring : Directory \"{dir}\" not found")
            return []
        logger.error(f"Directory \"{dir}\" not found", exc_info=EXEC_INFO)
        sys.exit(1)


def delete_folder(src):
    try:
        shutil.rmtree(src)
    except FileNotFoundError as e:
        logger.info(f'Ignoring : {e}')
        return


def print_json(data):
    logger.info(json.dumps(data, indent=2))


def parse_json(file):
    try:
        with open(file) as fl:
            doc = json.loads(fl.read())
        return doc
    except FileNotFoundError:
        logger.error(f"File \"{file}\" not found", exc_info=EXEC_INFO)
    return {}


def write_json(file, data):
    try:
        logger.info(f"Writing JSON to File {file}")
        with open(file, 'w') as fl:
            fl.write(json.dumps(data, indent=2))
    except FileNotFoundError:
        logger.error(f"File \"{file}\" not found", exc_info=EXEC_INFO)
        return False
    return True


def read_file(file_path):
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        return content
    except Exception as e:
        logger.error(f"Couldn't read file {file_path}. ERROR-INFO- {e}")


def write_file(file_path, data):
    try:
        with open(file_path, "wb") as f:
            f.write(data)
    except Exception as e:
        logger.error(f"Couldn't read file {file_path}. ERROR-INFO- {e}")


def compare_hash(data1, data2):
    try:
        data1_hash = hashlib.sha256(data1).hexdigest()
        data2_hash = hashlib.sha256(data2).hexdigest()
        if data1_hash == data2_hash:
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Hashes couldn't be matched. ERROR-INFO- {e}")


def get_proxy_endpoint_count(cfg):
    try:
        proxy_endpoint_count = cfg.getint('unifier', 'proxy_endpoint_count')
        max_proxy_endpoint_count = cfg.getint(
            'inputs', 'MAX_PROXY_ENDPOINT_LIMIT')
        if not (proxy_endpoint_count > 0 and proxy_endpoint_count <= max_proxy_endpoint_count):
            logger.error(
                'ERROR: Proxy Endpoints should be > Zero(0)  &  <=', max_proxy_endpoint_count)
            sys.exit(1)
    except ValueError:
        logger.error('proxy_endpoint_count should be a Number')
        sys.exit(1)

    return proxy_endpoint_count


def generate_env_groups_tfvars(project_id, env_config):
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
    with open(file_name, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        for each_row in rows:
            writer.writerow(each_row)

def retry(retries=3, delay=1, backoff=2):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == retries:
                        raise e
                    logger.info(f"Retrying {func.__name__} in {delay} seconds... (Attempt {attempt + 1})")
                    sleep(delay)
                    delay *= backoff
        return wrapper
    return decorator

def run_parallel(func, args, workers=10, max_retries=3, retry_delay=1):
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        # Initial futures (future: (arg, retry_count))
        future_to_arg_retry = {executor.submit(func, arg): (arg, 0) for arg in args}

        data = []
        while future_to_arg_retry:
            done, _ = concurrent.futures.wait(future_to_arg_retry, return_when=concurrent.futures.FIRST_COMPLETED)

            for future in done:
                arg, retry_count = future_to_arg_retry.pop(future)
                try:
                    data.append(future.result())
                except Exception as exc:
                    if retry_count < max_retries:
                        retry_count += 1
                        logger.warning(
                            f"Task with arg {arg} failed ({retry_count}/{max_retries} retries), retrying in {retry_delay} seconds...",
                            exc_info=True,
                        )
                        sleep(retry_delay)
                        future_to_arg_retry[executor.submit(func, arg)] = (arg, retry_count)
                    else:
                        data.append("Exception")
                        logger.error(
                            f"Task with arg {arg} failed after {max_retries} retries.",
                            exc_info=True
                        )
    return data

def get_proxy_entrypoint(dir):
    try:
        files = list_dir(dir)
        ent = []

        for eachfile in files:
            if eachfile.endswith(".xml"):

                ent.append(eachfile)
        if len(ent) == 1:
            return os.path.join(dir, ent[0])
        else:
            if len(ent) > 1:
                logger.error(
                    f"ERROR: Directory \"{dir}\" contains multiple xml files at root")
            else:
                logger.error(
                    f"ERROR: Directory \"{dir}\" has no xml file at root")
    except Exception as error:
        logger.info(f"INFO: get proxy endpoint module faced a {error}")
    finally:
        if len(ent) == 1:
            return os.path.join(dir, ent[0])
        else:
            return None


def parse_xml(file):
    try:
        with open(file) as fl:
            doc = xmltodict.parse(fl.read())
        return doc
    except FileNotFoundError:
        logger.error(f"File \"{file}\" not found", exc_info=EXEC_INFO)
    return {}


def get_proxy_files(dir, file_type='proxies'):
    target_dir = os.path.join(dir, file_type)
    files = list_dir(target_dir)
    xml_files = []
    for eachfile in files:
        if eachfile.endswith(".xml"):
            xml_files.append(os.path.splitext(eachfile)[0])
    if len(xml_files) == 0:
        logger.error(f"ERROR: Directory \"{target_dir}\" has no xml files")  # noqa
        return []
    else:
        return xml_files


def parse_proxy_root(dir):
    try:
        file = get_proxy_entrypoint(dir)
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
            proxies = get_proxy_files(dir)
            doc['APIProxy']['ProxyEndpoints']['ProxyEndpoint'] = proxies
        else:
            logger.info('Skipping with Filesystem parse of ProxyEndpoints')
        if len(target_endpoints) == 0:
            logger.info('Proceeding with Filesystem parse of TargetEndpoints')
            doc['APIProxy']['TargetEndpoints'] = {}
            targets = get_proxy_files(dir, 'targets')
            doc['APIProxy']['TargetEndpoints']['TargetEndpoint'] = targets
        else:
            logger.info('Skipping with Filesystem parse of TargetEndpoints')
        if len(policies) == 0:
            logger.info('Proceeding with Filesystem parse of Policies')
            doc['APIProxy']['Policies'] = {}
            policies_list = get_proxy_files(dir, 'policies')
            doc['APIProxy']['Policies']['Policy'] = policies_list
        else:
            logger.info('Skipping with Filesystem parse of Policies')
    except Exception as error:
        logger.error(f"raised in parse_proxy_root {error}")
    return doc


def parse_proxy_root_sharding(dir):

    file = get_proxy_entrypoint(dir)
    if file is None:
        return {}
    doc = parse_xml(file)
    return doc


def read_proxy_artifacts(dir, entrypoint):
    try:
        APIProxy = entrypoint['APIProxy']

        proxyName = entrypoint['APIProxy']['@name']
        proxy_dict = {
            'BasePaths': [],
            'Policies': {},
            'ProxyEndpoints': {},
            'TargetEndpoints': {},
            'proxyName': proxyName
        }

        ProxyEndpoints = APIProxy.get('ProxyEndpoints')
        if ProxyEndpoints is not None:
            ProxyEndpoints = APIProxy['ProxyEndpoints'].get('ProxyEndpoint')

            ProxyEndpoints = ([ProxyEndpoints] if isinstance(
                ProxyEndpoints, str) else ProxyEndpoints)
            for each_pe in ProxyEndpoints:
                proxy_dict['ProxyEndpoints'][each_pe] = parse_xml(
                    os.path.join(dir, 'proxies', f"{each_pe}.xml"))

            proxy_dict['BasePaths'] = APIProxy['Basepaths']

        if APIProxy.get('Policies') is not None:
            policies = APIProxy['Policies']['Policy']
            policies = ([policies] if isinstance(
                APIProxy['Policies']['Policy'], str) else policies)

            for each_policy in policies:
                proxy_dict['Policies'][each_policy] = parse_xml(
                    os.path.join(dir, 'policies', f"{each_policy}.xml"))

        if APIProxy.get('TargetEndpoints') is not None:

            TargetEndpoints = APIProxy['TargetEndpoints']['TargetEndpoint']
            TargetEndpoints = ([TargetEndpoints] if isinstance(
                TargetEndpoints, str) else TargetEndpoints)
            for each_te in TargetEndpoints:
                proxy_dict['TargetEndpoints'][each_te] = parse_xml(
                    os.path.join(dir, 'targets', f"{each_te}.xml"))
    except Exception as error:
        logger.error(f"Error: raised error in read_proxy_artifacts {error}")
    finally:
        return proxy_dict


def get_target_endpoints(ProxyEndpointData):
    target_endpoints = []
    routes = (
        [ProxyEndpointData['RouteRule']]
        if isinstance(ProxyEndpointData['RouteRule'], dict)
        else ProxyEndpointData['RouteRule']
    )
    for eachRoute in routes:
        if 'TargetEndpoint' in eachRoute:
            target_endpoints.append(eachRoute['TargetEndpoint'])
    return target_endpoints


def get_all_policies_from_step(Step):
    policies = []
    StepData = ([Step] if isinstance(Step, dict) else Step)
    for eachStep in StepData:
        policies.append(eachStep['Name'])
    return policies


def get_all_policies_from_flow(Flow, fault_rule=False):
    policies = []

    if not fault_rule:
        if Flow.get('Request'):
                if isinstance(Flow['Request'], list) and len(Flow['Request']) > 0:
                    Flow['Request'] = Flow['Request'][0]
                Request = ([] if Flow['Request'] is None else (
                            [] if Flow['Request'].get('Step') is None else (
                    [Flow['Request']['Step']] if isinstance(Flow['Request']['Step'], dict)
                    else Flow['Request']['Step']
                ))
                )
        else:
            Request = []
        if Flow.get('Response'):
            if isinstance(Flow['Response'], list) and len(Flow['Response']) > 0:
                    Flow['Response'] = Flow['Response'][0]
            Response = ([] if Flow['Response'] is None else (
                            [] if Flow['Response'].get('Step') is None else (
                        [Flow['Response']['Step']] if isinstance(Flow['Response']['Step'], dict)
                        else Flow['Response']['Step']
                        ))
                        )
        else:
            Response = []
        for each_flow in Request:
            policies.extend(get_all_policies_from_step(each_flow))
        for each_flow in Response:
            policies.extend(get_all_policies_from_step(each_flow))
    else:
        if Flow is None :
            FaultRules = []
        elif Flow.get('FaultRule', None) is None:
            FaultRules = []
        else:
            FaultRules = (
                [Flow.get('Step')] if isinstance(Flow['FaultRule'].get('Step'), dict)
                else Flow['FaultRule'].get('Step')
            )
        '''
        if Flow is None :
            FaultRules = []
        else :
            if isinstance(Flow, list) :
                if 'Step' in Flow :
                    FaultRules = ([Flow['Step']] if isinstance(Flow['Step'],dict) else Flow['Step'])
                else:
                    FaultRules = []
                    
        '''
        for each_step in FaultRules:
            policies.extend(get_all_policies_from_step(each_step))
    return policies


def get_all_policies_from_endpoint(endpointData, endpointType):
    policies = []
    policies.extend(
        get_all_policies_from_flow(
            endpointData[endpointType]['PreFlow']
        ) if endpointData[endpointType].get('PreFlow') else []
    )
    policies.extend(
        get_all_policies_from_flow(
            endpointData[endpointType]['PostFlow']
        ) if endpointData[endpointType].get('PostFlow') else []
    )

    if (isinstance(endpointData[endpointType].get('Flows'), list) and
        len(endpointData[endpointType].get('Flows')) > 0):
        endpointData[endpointType]['Flows'] = endpointData[endpointType]['Flows'][0]

    Flows = (
        []
        if endpointData[endpointType].get('Flows') is None else
        ( [] if endpointData[endpointType].get('Flows').get('Flow') is None
        else (
            [endpointData[endpointType]['Flows']['Flow']]
            if isinstance(
                endpointData[endpointType]['Flows']['Flow'], dict)
            else
            endpointData[endpointType]['Flows']['Flow']
        )))

    for eachFlow in Flows:
        policies.extend(
            get_all_policies_from_flow(
                eachFlow
            )
        )
    if 'DefaultFaultRule' in endpointData[endpointType]:

        policies.extend(
            get_all_policies_from_flow(
                endpointData[endpointType]['DefaultFaultRule'], True)
        )

    return policies


def get_proxy_objects_relationships(proxy_dict):
    proxy_object_map = {}
    ProxyEndpoints = proxy_dict['ProxyEndpoints']
    for ProxyEndpoint, ProxyEndpointData in ProxyEndpoints.items():
        proxy_object_map[ProxyEndpoint] = {}

        target_endpoints = get_target_endpoints(
            ProxyEndpointData['ProxyEndpoint'])
        TargetEndpointsData = {
            te: proxy_dict['TargetEndpoints'][te] for te in target_endpoints}
        policies = []
        policies.extend(get_all_policies_from_endpoint(
            ProxyEndpointData, 'ProxyEndpoint'))
        for _, each_te in TargetEndpointsData.items():
            policies.extend(get_all_policies_from_endpoint(
                each_te, 'TargetEndpoint'))
        proxy_object_map[ProxyEndpoint] = {
            # 'Policies' : get_all_policies_from_endpoint(ProxyEndpointData,'ProxyEndpoint'),
            'Policies': policies,
            'BasePath': ProxyEndpointData['ProxyEndpoint']['HTTPProxyConnection'].get('BasePath'),
            'TargetEndpoints': target_endpoints,
            # 'Resources' : []
        }

    return proxy_object_map


def get_api_path_groups(each_api_info):
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
    processed_step = []
    if step is None:
        return processed_step
    elif isinstance(step['Step'], dict):
        processed_step = [apply_condition(step['Step'], condition)]
    elif isinstance(step['Step'], list):
        processed_step = [apply_condition(i, condition) for i in step['Step']]
    else:
        return processed_step
    return processed_step


def process_flow(flow, condition):
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
    processed_rr = []
    for each_rr in (route_rules if isinstance(route_rules, list)
                    else [route_rules]):
        each_processed_rr = apply_condition(each_rr, condition)
        processed_rr.append(each_processed_rr)
    return processed_rr


def apply_condition(step, condition):
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
    merged_pe = {'ProxyEndpoint': {}}
    for each_pe, each_pe_info in api_dict['ProxyEndpoints'].items():
        if each_pe in pes:
            original_basepath = each_pe_info['ProxyEndpoint']['HTTPProxyConnection']['BasePath']   # noqa
            # TODO : Build full Request path
            condition = (original_basepath if original_basepath is None else f'(request.path Matches "{original_basepath}*")')   # noqa
            copied_flows = (
                None if each_pe_info['ProxyEndpoint']['Flows'] is None else each_pe_info['ProxyEndpoint']['Flows'].copy()   # noqa
            )
            original_flows = ([] if copied_flows is None else
                              ([copied_flows['Flow']] if isinstance(copied_flows['Flow'], dict) else copied_flows['Flow']))  # noqa

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

                merged_pe['ProxyEndpoint']['Description'] = each_pe_info['ProxyEndpoint']['Description']  # noqa
                merged_pe['ProxyEndpoint']['FaultRules'] = each_pe_info['ProxyEndpoint']['FaultRules']  # noqa
                merged_pe['ProxyEndpoint']['HTTPProxyConnection']['BasePath'] = (basepath if basepath is None else f'/{basepath}')  # noqa
                merged_pe['ProxyEndpoint']['HTTPProxyConnection']['Properties'] = each_pe_info['ProxyEndpoint']['HTTPProxyConnection']['Properties']  # noqa
                merged_pe['ProxyEndpoint']['HTTPProxyConnection']['VirtualHost'] = each_pe_info['ProxyEndpoint']['HTTPProxyConnection']['VirtualHost']  # noqa

            merged_pe['ProxyEndpoint']['@name'].append(each_pe_info['ProxyEndpoint']['@name'])  # noqa
            merged_pe['ProxyEndpoint']['RouteRule'].extend(
                    process_route_rules(each_pe_info['ProxyEndpoint']['RouteRule'], condition)  # noqa
            )
            merged_pe['ProxyEndpoint']['PreFlow']['Request']['Step'].extend(
                process_steps(each_pe_info['ProxyEndpoint']['PreFlow']['Request'], condition)  # noqa
            )
            merged_pe['ProxyEndpoint']['PreFlow']['Response']['Step'].extend(
                process_steps(each_pe_info['ProxyEndpoint']['PreFlow']['Response'], condition)  # noqa
            )
            merged_pe['ProxyEndpoint']['PostFlow']['Request']['Step'].extend(
                process_steps(each_pe_info['ProxyEndpoint']['PostFlow']['Request'], condition)  # noqa
            )
            merged_pe['ProxyEndpoint']['PostFlow']['Response']['Step'].extend(
                process_steps(each_pe_info['ProxyEndpoint']['PostFlow']['Response'], condition)  # noqa
            )
            if 'PostClientFlow' in each_pe_info['ProxyEndpoint']:
                merged_pe['ProxyEndpoint']['PostClientFlow'] = {
                    '@name': 'PostClientFlow',
                    'Request': {'Step': []},
                    'Response': {'Step': []},
                }
                merged_pe['ProxyEndpoint']['PostClientFlow']['Response']['Step'].extend(  # noqa
                    process_steps(each_pe_info['ProxyEndpoint']['PostClientFlow']['Response'], None)  # noqa
                )
            for each_flow in original_flows:
                merged_pe['ProxyEndpoint']['Flows']['Flow'].append(
                    process_flow(each_flow, condition)
                )
    merged_pe['ProxyEndpoint']['@name'] = "-".join(merged_pe['ProxyEndpoint']['@name'])  # noqa
    return merged_pe


def export_debug_log(files, log_path='logs'):
    create_dir(log_path)
    for file, data in files.items():
        file_name = f'{log_path}/{file}.json'
        write_json(file_name, data)


def delete_file(src):
    try:
        os.remove(src)
    except FileNotFoundError as e:
        logger.info(f'Ignoring : {e}')
        return


def write_xml_from_dict(file, data):
    try:
        with open(file, 'w') as fl:
            fl.write(xmltodict.unparse(data, pretty=True))
    except FileNotFoundError:
        logger.error(f"ERROR: File \"{file}\" not found")
        return False
    return True


def copy_folder(src, dst):
    try:
        shutil.copytree(src, dst)
    except FileNotFoundError as e:
        logger.error(e)
        sys.exit(1)


def clean_up_artifacts(target_dir, artifacts_to_retains):
    for file in list_dir(target_dir, True):
        each_policy_file = file.split('.xml')[0]
        if each_policy_file not in artifacts_to_retains:
            delete_file(f"{target_dir}/{file}")


def filter_objects(obj_data, obj_type, targets):
    result = None
    if obj_data is None:
        return result
    elif isinstance(obj_data.get(obj_type), str):
        result = ({obj_type: obj_data[obj_type]} if obj_data[obj_type] in targets else None)  # noqa
    elif isinstance(obj_data.get(obj_type), list):
        result = {obj_type: [v for v in obj_data[obj_type] if v in targets]}
    else:
        return result
    return result


def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file),
                       os.path.relpath(os.path.join(root, file),
                                       os.path.join(path, '..')))


def clone_proxies(source_dir, target_dir,
                  objects, merged_pes, proxy_bundle_directory):
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
            root['APIProxy']['TargetEndpoints'], 'TargetEndpoint', objects['TargetEndpoints'])  # noqa
        clean_up_artifacts(f"{target_dir}/policies", objects['Policies'])
        clean_up_artifacts(f"{target_dir}/targets", objects['TargetEndpoints'])
        for pe in objects['ProxyEndpoints']:
            write_xml_from_dict(
                f"{target_dir}/proxies/{pe}.xml", merged_pes[pe])
        clean_up_artifacts(f"{target_dir}/proxies", objects['ProxyEndpoints'])
        root['APIProxy']['ProxyEndpoints'] = {'ProxyEndpoint': (
            objects['ProxyEndpoints'] if len(objects['ProxyEndpoints']) > 1 else objects['ProxyEndpoints'][0])}  # noqa
        transformed_file = file.split('/')
        transformed_file[-1] = f"{objects['Name']}.xml"
        write_xml_from_dict("/".join(transformed_file), root)
        delete_folder(f"{target_dir}/manifests")

        with zipfile.ZipFile(f"{proxy_bundle_directory}/{objects['Name']}.zip", 'w', zipfile.ZIP_DEFLATED) as zipf:  # noqa
            zipdir(target_dir, zipf)

    except Exception as error:
        logger.error(
            f"some error occurred in clone proxy function error. ERROR-INFO - {error}")
    finally:
        return merged_pes
