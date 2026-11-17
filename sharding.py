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

"""Handles sharding and proxy splitting logic
for Apigee proxies.
"""


import os
import utils
import unifier
from base_logger import logger


def qualification_report_info(each_proxy_dict):
    """Generates a qualification report for a \
    given proxy.

    Analyzes a proxy's configuration and \
    identifies potential issues
    related to policies, anti-patterns, and \
    multiple base paths.

    Args:
        each_proxy_dict (dict): A dictionary \
        containing the proxy's
            configuration details.

    Returns:
        dict: A dictionary containing the \
        qualification report.
    """
    report = {}

    report['policies'] = {}
    report['JsonPathEnabled'] = {}
    report['AntiPatternQuota'] = {}
    report['CacheWithoutExpiry'] = {}
    for policy, value in each_proxy_dict['Policies'].items():

        # JSONPath Enabled
        if list(value.keys())[0] == 'ExtractVariables':
            jp_count = len(value['ExtractVariables'].get('JSONPayload', {}).get('Variable', {}))  # noqa pylint: disable=C0301
            if jp_count > 0:
                report['JsonPathEnabled'][policy] = jp_count

        # Quota Policy Anti Pattern
        if list(value.keys())[0] == 'Quota':
            if (value['Quota'].get('Distributed', 'false') == 'false' or
                    value['Quota'].get('Synchronous', 'false') == 'true'):
                report['AntiPatternQuota'][policy] = {}
                report['AntiPatternQuota'][policy]['distributed'] = value['Quota'].get('Distributed', None)  # noqa pylint: disable=C0301
                report['AntiPatternQuota'][policy]['Synchronous'] = value['Quota'].get('Synchronous', None)  # noqa pylint: disable=C0301

        # Unsupported Policies
        unsupported_policies = ['OAuthV1', 'ConcurrentRatelimit',
                                'ConnectorCallout', 'StatisticsCollector',
                                'DeleteOAuthV1Info', 'GetOAuthV1Info',
                                'Ldap']
        if list(value.keys())[0] in unsupported_policies:
            report['policies'][policy] = list(value.keys())[0]

        # Cache without expiry
        if list(value.keys())[0] == 'PopulateCache' or list(value.keys())[0] == 'ResponseCache':  # noqa pylint: disable=C0301
            if not value[list(value.keys())[0]].get('ExpirySettings'):
                report['CacheWithoutExpiry'][policy] = list(value.keys())[0]

    # api with multiple basepaths
    base_paths = []
    for _, value in each_proxy_dict['ProxyEndpoints'].items():  # noqa pylint: disable=C0301
        basepath = value['ProxyEndpoint']['HTTPProxyConnection']['BasePath']  # noqa pylint: disable=C0301
        base_paths.append(basepath)
    report['base_paths'] = base_paths

    return report


def unzip_all_bundles(input_cfg):
    """Unzips all proxy bundles in the specified \
    directory.

    Args:
        input_cfg \
        (configparser.ConfigParser): \
        The input configuration.
    """
    backend_cfg = utils.parse_config('backend.properties')
    export_dir_name = backend_cfg.get('export', 'EXPORT_DIR')
    target_dir = input_cfg.get('inputs', 'TARGET_DIR')
    source_unzipped_apis = backend_cfg.get('unifier', 'source_unzipped_apis')  # noqa pylint: disable=C0301

    extension = ".zip"
    export_base_dir = utils.safe_join_path(target_dir, export_dir_name)
    apis_dir = utils.safe_join_path(export_base_dir, "apis")
    unzip_dir_name = utils.safe_join_path(
        export_base_dir, source_unzipped_apis.lstrip('/')
    )

    if not os.path.isdir(unzip_dir_name):
        os.makedirs(unzip_dir_name)  # create unzip directory

    for item in os.listdir(apis_dir):  # loop through items in dir
        if item.endswith(extension):  # check for ".zip" extension
            archive_stem = item[:-4]
            try:
                utils.validate_path_component(archive_stem)
                file_name = utils.safe_join_path(apis_dir, item)
                target_extract_dir = utils.safe_join_path(
                    unzip_dir_name, archive_stem
                )
                utils.safe_extract_zip(file_name, target_extract_dir)
            except ValueError as err:
                logger.error(
                    "Skipping unsafe archive %r: %s", item, err
                )


def proxy_dependency_map(cfg, export_data):  # noqa pylint: disable=R0914
    """Creates a proxy dependency map.

    This function generates a map indicating \
    the dependencies of each proxy,
    including shared flows, KVMs, target servers, \
    and references.

    Args:
        cfg (configparser.ConfigParser): The \
        input configuration.
        exportData (dict): The exported Apigee \
        data.

    Returns:
        dict: A dictionary representing the \
        proxy dependency map.
    """

    unzip_all_bundles(cfg)

    input_cfg = utils.parse_config('input.properties')
    backend_cfg = utils.parse_config('backend.properties')
    export_dir_name = backend_cfg.get('export', 'EXPORT_DIR')
    target_dir = input_cfg.get('inputs', 'TARGET_DIR')
    source_unzipped_apis = backend_cfg.get('unifier', 'source_unzipped_apis')  # noqa pylint: disable=C0301

    current_dir = os.getcwd()
    apis_dirs = current_dir+'/'+target_dir+'/'+export_dir_name+source_unzipped_apis  # noqa pylint: disable=C0301

    result = {}
    proxy_dir = apis_dirs
    proxy_dependency_map_data = {}
    args = ((apiname, proxy_dir, proxy_dependency_map_data)
            for apiname in export_data["orgConfig"]["apis"].keys())

    result = utils.run_parallel(proxy_dependency_map_parallel, args)
    res = {}
    for item in result:
        for key, value in item.items():
            res[key] = value

    return res


def proxy_dependency_map_parallel(arg_tuple):  # noqa pylint: disable=R0914
    """Executes proxy dependency mapping in \
    parallel.

    Args:
        arg_tuple (tuple): A tuple containing \
        the API name,
            proxy directory, and proxy dependency \
            map.

    Returns:
        dict: The proxy dependency map for the \
        processed API.
    """
    try:
        each_dir = arg_tuple[0]
        proxy_dir = arg_tuple[1]
        proxy_dependency_map_data = arg_tuple[2]
        logger.info(f"processing {each_dir}")  # noqa pylint: disable=W1203
        utils.validate_path_component(each_dir)
        apiproxy_dir = utils.safe_join_path(proxy_dir, each_dir, "apiproxy")
        if not os.path.exists(apiproxy_dir):
            proxy_dependency_map_data[each_dir] = {
                'is_split': False
            }
            return proxy_dependency_map_data
        each_proxy_dict = utils.read_proxy_artifacts(
            apiproxy_dir,
            utils.parse_proxy_root_sharding(apiproxy_dir),
        )

        each_proxy_rel = utils.get_proxy_objects_relationships(each_proxy_dict)  # noqa pylint: disable=C0301
        proxy_dependency_map_data[each_dir] = {}

        # checking if the pe > count_provided
        cfg = utils.parse_config('backend.properties')
        proxy_endpoint_cnt = utils.get_proxy_endpoint_count(cfg)
        input_cfg = utils.parse_config('input.properties')
        export_dir_name = cfg.get('export', 'EXPORT_DIR')
        target_dir = input_cfg.get('inputs', 'TARGET_DIR')
        unifier_output_dir = cfg.get('unifier', 'unifier_output_dir')

        if len(each_proxy_rel.keys()) > proxy_endpoint_cnt:

            proxy_split_result = unifier.proxy_unifier(each_dir)
            proxy_dependency_map_data[each_dir]["is_split"] = True
            proxy_dependency_map_data[each_dir]["split_output_names"] = []
            for dir_name in proxy_split_result:
                utils.validate_path_component(dir_name)
                unifier_apiproxy_dir = utils.safe_join_path(
                    target_dir,
                    export_dir_name,
                    unifier_output_dir.lstrip('/'),
                    dir_name,
                    "apiproxy",
                )
                proxy_dependency_map_data[dir_name] = {}
                proxy_dict = utils.read_proxy_artifacts(
                    unifier_apiproxy_dir,
                    utils.parse_proxy_root_sharding(unifier_apiproxy_dir),
                )

                proxy_rel = utils.get_proxy_objects_relationships(proxy_dict)
                proxy_dependency_map_data = build_proxy_dependency(
                    proxy_dependency_map_data, proxy_rel, proxy_dict, dir_name)
                proxy_dependency_map_data[dir_name]["qualification"] = qualification_report_info(  # noqa pylint: disable=C0301
                    proxy_dict)
                proxy_dependency_map_data[dir_name]["unifier_created"] = True
                proxy_dependency_map_data[each_dir]["split_output_names"].append(  # noqa pylint: disable=C0301
                    dir_name)
        else:
            proxy_dependency_map_data = build_proxy_dependency(
                proxy_dependency_map_data, each_proxy_rel, each_proxy_dict, each_dir)  # noqa pylint: disable=C0301
        proxy_dependency_map_data[each_dir]["qualification"] = qualification_report_info(  # noqa pylint: disable=C0301
            each_proxy_dict)

    except Exception as error:   # noqa pylint: disable=W0718
        logger.error(  # noqa pylint: disable=W1203
            f"Error in proxy dependency map parallel function. ERROR-INFO - {error} {each_dir}")  # noqa pylint: disable=C0301
        proxy_dependency_map_data[each_dir] = {
            'is_split': False
        }
    return proxy_dependency_map_data


def build_proxy_dependency(proxy_dependency_map_data, each_proxy_rel,  # noqa pylint: disable=R0912
                           each_proxy_dict, each_dir):
    """Builds the proxy dependency map for a \
    single proxy.

    Args:
        proxyDependencyMap (dict): The proxy \
        dependency map
            being built.
        each_proxy_rel (dict): The relationships \
        between
            proxy objects.
        each_proxy_dict (dict): The proxy \
        configuration details.
        each_dir (str): The directory of the \
        proxy.

    Returns:
        dict: The updated proxy dependency map.
    """
    for proxyname, _ in each_proxy_rel.items():  # noqa pylint: disable=R1702
        if each_proxy_rel[proxyname].get('Policies') is not None:
            for eachpolicy in each_proxy_rel[proxyname]['Policies']:
                if "FlowCallout" in list(each_proxy_dict['Policies'][eachpolicy].keys()):  # noqa pylint: disable=C0301
                    if "SharedFlowBundle" in each_proxy_dict['Policies'][eachpolicy]["FlowCallout"]:  # noqa pylint: disable=C0301
                        if not proxy_dependency_map_data[each_dir].get('SharedFlow'):  # noqa pylint: disable=C0301
                            proxy_dependency_map_data[each_dir]['SharedFlow'] = [  # noqa pylint: disable=C0301
                                each_proxy_dict['Policies'][eachpolicy]["FlowCallout"]["SharedFlowBundle"]]  # noqa pylint: disable=C0301
                        else:
                            proxy_dependency_map_data[each_dir]['SharedFlow'].append(  # noqa pylint: disable=C0301
                                each_proxy_dict['Policies'][eachpolicy]["FlowCallout"]["SharedFlowBundle"])  # noqa pylint: disable=C0301

                if "KeyValueMapOperations" in list(each_proxy_dict['Policies'][eachpolicy].keys()):  # noqa pylint: disable=C0301
                    kvmname = each_proxy_dict['Policies'][eachpolicy]['KeyValueMapOperations'].get(  # noqa pylint: disable=C0301
                        '@mapIdentifier')
                    if not proxy_dependency_map_data[each_dir].get('KVM'):
                        proxy_dependency_map_data[each_dir]['KVM'] = [kvmname]
                    else:
                        proxy_dependency_map_data[each_dir]['KVM'].append(kvmname)  # noqa pylint: disable=C0301

        if each_proxy_rel[proxyname].get('TargetEndpoints') is not None:
            for eachtargetendpoint in each_proxy_rel[proxyname]['TargetEndpoints']:  # noqa pylint: disable=C0301
                if 'HostedTarget' in each_proxy_dict['TargetEndpoints'][eachtargetendpoint]['TargetEndpoint'].keys():  # noqa pylint: disable=C0301
                    return proxy_dependency_map_data
                if 'LocalTargetConnection' in each_proxy_dict['TargetEndpoints'][eachtargetendpoint]['TargetEndpoint'].keys():  # noqa pylint: disable=C0301
                    return proxy_dependency_map_data
                targetservers = each_proxy_dict['TargetEndpoints'][eachtargetendpoint]['TargetEndpoint']['HTTPTargetConnection'].get(  # noqa pylint: disable=C0301
                    'LoadBalancer')
                if targetservers is not None:
                    if isinstance(targetservers.get('Server'), dict):
                        if not proxy_dependency_map_data[each_dir].get("TargetServer"):  # noqa pylint: disable=C0301
                            proxy_dependency_map_data[each_dir]["TargetServer"] = [  # noqa pylint: disable=C0301
                                targetservers.get('@name')]
                        else:
                            proxy_dependency_map_data[each_dir]["TargetServer"].append(  # noqa pylint: disable=C0301
                                targetservers.get('@name'))
                    else:
                        for targetdict in targetservers.get('Server'):
                            if not proxy_dependency_map_data[each_dir].get("TargetServer"):  # noqa pylint: disable=C0301
                                proxy_dependency_map_data[each_dir]["TargetServer"] = [  # noqa pylint: disable=C0301
                                    targetdict.get('@name')]
                            else:
                                proxy_dependency_map_data[each_dir]["TargetServer"].append(  # noqa pylint: disable=C0301
                                    targetdict.get('@name'))
                else:
                    if each_proxy_dict['TargetEndpoints'][eachtargetendpoint]['TargetEndpoint']['HTTPTargetConnection'].get('SSLInfo'):  # noqa pylint: disable=C0301
                        sslinfo = each_proxy_dict['TargetEndpoints'][eachtargetendpoint]['TargetEndpoint']['HTTPTargetConnection'].get(  # noqa pylint: disable=C0301
                            'SSLInfo')
                        if not proxy_dependency_map_data[each_dir].get("References"):  # noqa pylint: disable=C0301
                            proxy_dependency_map_data[each_dir]["References"] = [  # noqa pylint: disable=C0301
                                {"Keystore": sslinfo.get('KeyStore'), "Trustore": sslinfo.get('TrustStore')}]  # noqa pylint: disable=C0301
                        else:
                            proxy_dependency_map_data[each_dir]["References"].append(  # noqa pylint: disable=C0301
                                {"Keystore": sslinfo.get('KeyStore'), "Trustore": sslinfo.get('TrustStore')})  # noqa pylint: disable=C0301

    return proxy_dependency_map_data


def sharding_wrapper(proxy_dependency_map_data, export_data):
    """Manages environment sharding based on \
    proxy dependencies.

    Distributes proxies and shared flows across \
    environments
    based on configured limits and dependencies, \
    handling
    split proxies.

    Args:
        proxyDependencyMap (dict): Proxy \
        dependency map.
        exportData (dict): Exported Apigee data.

    Returns:
        dict: Sharding results per environment.
    """
    shard_result = {}

    for env, values in export_data["envConfig"].items():
        result_dict = {}
        for apiname in values["apis"].keys():
            if proxy_dependency_map_data[apiname].get("is_split") is not True:
                result_dict[apiname] = proxy_dependency_map_data[apiname]
            else:
                for splits in proxy_dependency_map_data[apiname]["split_output_names"]:  # noqa pylint: disable=C0301
                    result_dict[splits] = proxy_dependency_map_data[splits]

        result = environment_sharding(env, result_dict)
        shard_result[env] = result[0]
        shard_result[env]["not_processed_apis"] = result[1]

    return shard_result


def environment_sharding(env, proxy_dependency_map_data):  # noqa pylint: disable=R0912
    """Implements sharding logic for a single \
    environment.

    Distributes proxies and shared flows within \
    an environment
    based on configured limits and dependencies.

    Args:
        env (str): Environment name.
        proxyDependencyMap (dict): Proxy \
        dependency map.

    Returns:
        tuple: (env_slot, notprocessed)
            env_slot: Dict of sharded proxies and \
            shared flows.
            notprocessed: Dict of proxies that \
            couldn't be
                processed due to shared flow limits.
    """
    # sort proxyDependencyMap in alphabetically order
    my_keys = list(proxy_dependency_map_data.keys())
    my_keys.sort()
    sorted_proxy_dependency_map = {i: proxy_dependency_map_data[i] for i in my_keys}  # noqa pylint: disable=C0301

    cfg = utils.parse_config('backend.properties')
    per_env_proxy_limit = cfg.getint('inputs', 'NO_OF_PROXIES_PER_ENV_LIMITS')  # noqa pylint: disable=C0301
    total_units_per_envn = cfg.getint(
        'inputs', 'NO_OF_PROXIES_AND_SHARED_FLOWS_PER_ENV_LIMITS')

    env_name = env
    env_slot = {}
    slot_cntr = 1
    notprocessed = {}
    for apiname, dependencies in sorted_proxy_dependency_map.copy().items():
        if dependencies.get("SharedFlow") and len(dependencies.get("SharedFlow")) > (total_units_per_envn-1):  # noqa pylint: disable=C0301
            notprocessed[apiname] = dependencies
            del sorted_proxy_dependency_map[apiname]

    while sorted_proxy_dependency_map:

        if not env_slot or not env_slot.get(env_name+str(slot_cntr)):
            env_slot[env_name+str(slot_cntr)] = dict(
                {"proxyname": [], "shared_flow": [], "target_server": []})

        # check total proxies in a slot
        if (len(env_slot[env_name+str(slot_cntr)]["proxyname"]) >= per_env_proxy_limit   # noqa pylint: disable=C0301
            or (len(env_slot[env_name+str(slot_cntr)]["proxyname"]) + len(env_slot[env_name+str(slot_cntr)]["shared_flow"]) >= total_units_per_envn)):  # noqa pylint: disable=C0301
            slot_cntr = slot_cntr + 1
            env_slot[env_name+str(slot_cntr)] = dict(
                {"proxyname": [], "shared_flow": [], "target_server": []})

        # add proxies and sharedflow provided sum of it <= than 60
        for apiname, dependencies in sorted_proxy_dependency_map.copy().items():  # noqa pylint: disable=C0301
            if (len(env_slot[env_name+str(slot_cntr)]["proxyname"]) < per_env_proxy_limit  # noqa pylint: disable=C0301
                and ((len(env_slot[env_name+str(slot_cntr)]["proxyname"]) + len(find_unique_items(dependencies.get("SharedFlow"), env_slot[env_name+str(slot_cntr)]["shared_flow"]))) < total_units_per_envn)):  # noqa pylint: disable=C0301

                # add proxy name
                env_slot[env_name+str(slot_cntr)]["proxyname"].append(apiname)  # noqa pylint: disable=C0301

                # add unique shared flows

                unique_shared_flow = find_unique_items(
                    env_slot[env_name+str(slot_cntr)]["shared_flow"], dependencies.get("SharedFlow"))  # noqa pylint: disable=C0301
                if unique_shared_flow:
                    env_slot[env_name+str(slot_cntr)]["shared_flow"].clear()  # noqa pylint: disable=C0301
                    env_slot[env_name+str(slot_cntr)
                             ]["shared_flow"].extend(unique_shared_flow)

                # add unique target servers
                unique_target_server = find_unique_items(
                    env_slot[env_name+str(slot_cntr)]["target_server"], dependencies.get("TargetServer"))  # noqa pylint: disable=C0301
                if unique_target_server:
                    env_slot[env_name+str(slot_cntr)]["target_server"].clear()  # noqa pylint: disable=C0301
                    env_slot[env_name+str(slot_cntr)
                             ]["target_server"].extend(unique_target_server)  # noqa pylint: disable=C0301

                # remove proxy from proxy dependency map
                del sorted_proxy_dependency_map[apiname]

        # add proxies that have same sharedflow
        for apiname, dependencies in sorted_proxy_dependency_map.copy().items():  # noqa pylint: disable=C0301

            if len(env_slot[env_name+str(slot_cntr)]["proxyname"]) < per_env_proxy_limit and ((len(env_slot[env_name+str(slot_cntr)]["proxyname"]) + len(find_unique_items(dependencies.get("SharedFlow"), env_slot[env_name+str(slot_cntr)]["shared_flow"]))) < total_units_per_envn):  # noqa pylint: disable=C0301

                if is_subset(dependencies.get("SharedFlow"), env_slot[env_name+str(slot_cntr)].get("shared_flow")):  # noqa pylint: disable=C0301
                    # add proxy name
                    env_slot[env_name+str(slot_cntr)
                             ]["proxyname"].append(apiname)

                    # add unique target servers
                    if dependencies.get("TargetServer"):
                        unique_target_server = find_unique_items(
                            env_slot[env_name+str(slot_cntr)]["target_server"], dependencies.get("TargetServer"))  # noqa pylint: disable=C0301
                        env_slot[env_name+str(slot_cntr)
                                 ]["target_server"].clear()
                        env_slot[env_name+str(slot_cntr)
                                 ]["target_server"].extend(unique_target_server)  # noqa pylint: disable=C0301

                    # remove proxy from proxy dependency map
                    del sorted_proxy_dependency_map[apiname]

        # add proxies that do not have sharedflow but share same target servers  # noqa pylint: disable=C0301
        for apiname, dependencies in sorted_proxy_dependency_map.copy().items():  # noqa pylint: disable=C0301

            if len(env_slot[env_name+str(slot_cntr)]["proxyname"]) < per_env_proxy_limit and ((len(env_slot[env_name+str(slot_cntr)]["proxyname"]) + len(find_unique_items(dependencies.get("SharedFlow"), env_slot[env_name+str(slot_cntr)]["shared_flow"]))) < total_units_per_envn):  # noqa pylint: disable=C0301

                if not dependencies.get('SharedFlow') and is_subset(dependencies.get("TargetServer"), env_slot[env_name+str(slot_cntr)].get("target_server")):  # noqa pylint: disable=C0301
                    # add proxy name
                    env_slot[env_name+str(slot_cntr)
                             ]["proxyname"].append(apiname)

                    # remove from proxy dependency map
                    del sorted_proxy_dependency_map[apiname]

        # add proxies that do not have any shareflow and target servers
        for apiname, dependencies in sorted_proxy_dependency_map.copy().items():  # noqa pylint: disable=C0301
            if not dependencies.get("SharedFlow") and not dependencies.get("TargetServer"):  # noqa pylint: disable=C0301

                if len(env_slot[env_name+str(slot_cntr)]["proxyname"]) < per_env_proxy_limit and ((len(env_slot[env_name+str(slot_cntr)]["proxyname"]) + len(find_unique_items(dependencies.get("SharedFlow"), env_slot[env_name+str(slot_cntr)]["shared_flow"]))) < total_units_per_envn):  # noqa pylint: disable=C0301
                    # add proxy name
                    env_slot[env_name+str(slot_cntr)
                             ]["proxyname"].append(apiname)

                    # remove from proxy dependency map
                    del sorted_proxy_dependency_map[apiname]

        slot_cntr = slot_cntr+1
    return [env_slot, notprocessed]


def find_unique_items(list1, list2):
    """Finds the union of two lists, preserving \
        unique items.

    Args:
        list1 (list): First list.
        list2 (list): Second list.

    Returns:
        set or list: Union of unique items, or \
        original
                    list if only one is provided.
    """
    if list1 and list2:
        unique_items = set(list1) | set(list2)
        return unique_items
    if list1:
        return list1
    return list2


def is_subset(list1, list2):
    """Returns True if list1 is a subset of list2, False otherwise."""
    if not list1 or not list2:
        return True

    for item in list1:
        if item not in list2:
            return False

    return True
