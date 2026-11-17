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
# limitations under the License.

"""Handles proxy unification and splitting logic.

This module provides functionalities for
unifying and splitting Apigee proxies based on
configuration and path analysis. It processes
proxy artifacts, analyzes their dependencies,
and generates modified proxy bundles.
"""

import utils  # pylint: disable=import-error
from base_logger import logger

DEFAULT_GCP_ENV_TYPE = 'BASE'


def proxy_unifier(proxy_dir_name):  # noqa pylint: disable=R0914
    """Unifies and splits proxies based on path analysis.

    Processes proxy artifacts, analyzes
    dependencies, and generates modified proxy
    bundles based on path grouping and
    configuration.

    Args:
        proxy_dir_name (str): The name of the
            proxy directory.

    Returns:
        dict: A dictionary containing merged
            proxy objects information.
    """
    try:
        inputs_cfg = utils.parse_config('input.properties')

        cfg = utils.parse_config('backend.properties')
        export_base = utils.safe_join_path(
            inputs_cfg.get('inputs', 'TARGET_DIR'),
            cfg.get('export', 'EXPORT_DIR'),
        )
        proxy_dir = utils.safe_join_path(
            export_base,
            cfg['unifier']['source_unzipped_apis'].lstrip('/'),
        )
        proxy_dest_dir = utils.safe_join_path(
            export_base,
            cfg['unifier']['unifier_output_dir'].lstrip('/'),
        )
        proxy_bundle_directory = utils.safe_join_path(
            export_base,
            cfg['unifier']['unifier_zipped_bundles'].lstrip('/'),
        )

        export_debug_file = cfg.getboolean('unifier', 'debug')

        utils.create_dir(proxy_bundle_directory)
        proxy_endpoint_count = utils.get_proxy_endpoint_count(cfg)

        final_dict = {}
        processed_dict = {}
        each_dir = utils.validate_path_component(proxy_dir_name)
        source_apiproxy_dir = utils.safe_join_path(
            proxy_dir, each_dir, "apiproxy"
        )

        each_proxy_dict = utils.read_proxy_artifacts(
            source_apiproxy_dir,
            utils.parse_proxy_root(source_apiproxy_dir),
        )

        if len(each_proxy_dict) > 0:
            each_proxy_rel = utils.get_proxy_objects_relationships(
                each_proxy_dict)
            final_dict[each_dir] = each_proxy_dict
            processed_dict[each_dir] = each_proxy_rel

        processing_final_dict = final_dict.copy()

        path_group_map = {}
        for each_api, each_api_info in processed_dict.items():
            path_group_map[each_api] = utils.get_api_path_groups(each_api_info)  # noqa

        grouped_apis = {}
        for each_api, base_path_info in path_group_map.items():
            grouped_apis[each_api] = utils.group_paths_by_path(
                base_path_info, proxy_endpoint_count)

        bundled_group = {}
        for each_api, grouped_api in grouped_apis.items():
            bundled_group[each_api] = utils.bundle_path(grouped_api)

        merged_pes = {}
        merged_objects = {}
        for each_api, grouped_api in bundled_group.items():
            for index, each_group in enumerate(grouped_api):
                merged_objects[f"{each_api}_{index}"] = {
                    'Policies': [],
                    'TargetEndpoints': [],
                    'ProxyEndpoints': []
                }
                for each_path, pes in each_group.items():
                    each_pe = '-'.join(pes)
                    merged_pes[each_pe] = utils.merge_proxy_endpoints(
                        processing_final_dict[each_api],
                        each_path,
                        pes
                    )
                    proxy_name = utils.validate_path_component(
                        final_dict[each_api]['proxyName']
                    )
                    merged_objects[f"{each_api}_{index}"]['Name'] = f"{proxy_name}_{index}"  # noqa pylint: disable=C0301
                    merged_objects[f"{each_api}_{index}"]['Policies'].extend(  # noqa
                        [item for pe in pes for item in processed_dict[each_api][pe]['Policies']])   # noqa pylint: disable=C0301
                    merged_objects[f"{each_api}_{index}"]['TargetEndpoints'].extend(  # noqa
                        [item for pe in pes for item in processed_dict[each_api][pe]['TargetEndpoints']])  # noqa pylint: disable=C0301
                    merged_objects[f"{each_api}_{index}"]['Policies'] = list(set(merged_objects[f"{each_api}_{index}"]['Policies']))  # noqa pylint: disable=C0301
                    merged_objects[f"{each_api}_{index}"]['TargetEndpoints'] = list(set(merged_objects[f"{each_api}_{index}"]['TargetEndpoints']))  # noqa pylint: disable=C0301
                    merged_objects[f"{each_api}_{index}"]['ProxyEndpoints'].append(each_pe)  # noqa

        for each_api, grouped_api in bundled_group.items():
            for index, each_group in enumerate(grouped_api):

                utils.clone_proxies(
                    utils.safe_join_path(proxy_dir, each_api, "apiproxy"),
                    utils.safe_join_path(
                        proxy_dest_dir, f"{each_api}_{index}"
                    ),
                    merged_objects[f"{each_api}_{index}"],
                    merged_pes,
                    proxy_bundle_directory
                )

        files = {
            'final_dict': final_dict,
            'processed_dict': processed_dict,
            'path_group_map': path_group_map,
            'grouped_apis': grouped_apis,
            'bundled_group': bundled_group,
            'merged_pes': merged_pes,
            'merged_objects': merged_objects,
        }
        if export_debug_file:
            utils.export_debug_log(files)

    except Exception as error:  # noqa pylint: disable=W0718
        logger.error(  # noqa pylint: disable=W1203
            f"ERROR : Some error occured in unifier module. ERROR-INFO - {error}")  # noqa pylint: disable=W1203
    return merged_objects
