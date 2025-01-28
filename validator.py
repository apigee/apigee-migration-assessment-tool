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

"""Validates Apigee artifacts against Apigee X or hybrid
requirements.

This module provides validation functionalities for
various Apigee artifacts like target servers, resource
files, proxy bundles, and flow hooks. It leverages
validation rules and mappings to assess the
compatibility of these artifacts with Apigee X or
hybrid environments.
"""

import copy
from assessment_mapping.targetservers import targetservers_mapping
from assessment_mapping.resourcefiles import resourcefiles_mapping
from nextgen import ApigeeNewGen
from utils import list_dir, retry


class ApigeeValidator():
    """Validates Apigee artifacts for Apigee X or hybrid.

    Provides methods to validate target servers, resource
    files, proxy bundles, and flow hooks against predefined
    rules and compatibility checks.
    """

    def __init__(self, project_id, token, env_type):
        """Initializes ApigeeValidator.

        Args:
            project_id (str): The Google Cloud project ID.
            token (str): The OAuth2 access token.
            env_type (str): The Apigee environment type
                ('hybrid' or 'x').
        """
        self.project_id = project_id
        self.xorhybrid = ApigeeNewGen(project_id, token, env_type)

    def validate_env_targetservers(self, target_servers):
        """Validates environment target servers.

        Args:
            target_servers (dict): A dictionary of target
                server configurations.

        Returns:
            list: A list of validated target server
                objects with importability status and
                reasons.
        """
        validation_targetservers = []
        for _, target_server_data in target_servers.items():
            obj = copy.copy(target_server_data)
            obj['importable'], obj['reason'] = self.validate_env_targetserver_resource(target_server_data)   # noqa pylint: disable=C0301
            validation_targetservers.append(obj)
        return validation_targetservers

    def validate_env_targetserver_resource(self, targetservers):
        """Validates a single target server resource.

        Args:
            targetservers (dict): The target server
                configuration.

        Returns:
            tuple: A tuple containing the importability
                status (bool) and a list of reasons
                (list).
        """
        errors = []
        for key in targetservers_mapping.keys():
            if targetservers[key] in targetservers_mapping[key]['invalid_values'].keys():  # noqa
                errors.append({
                    'key': key,
                    'error_msg': targetservers_mapping[key]['invalid_values'][targetservers[key]],   # noqa pylint: disable=C0301
                })

        if len(errors) == 0:
            return True, []
        return False, errors

    def validate_env_resourcefiles(self, resourcefiles):
        """Validates environment resource files.

        Args:
            resourcefiles (dict): A dictionary of
                resource file configurations.

        Returns:
            list: A list of validated resource file
                objects with importability status and
                reasons.
        """
        validation_rfiles = []
        for resourcefile in resourcefiles.keys():
            obj = copy.copy(resourcefiles[resourcefile])
            obj['importable'], obj['reason'] = self.validate_env_resourcefile_resource(resourcefiles[resourcefile])    # noqa pylint: disable=C0301
            validation_rfiles.append(obj)
        return validation_rfiles

    def validate_env_resourcefile_resource(self, metadata):
        """Validates a single resource file.

        Args:
            metadata (dict): Resource file metadata.

        Returns:
            tuple: Importability status (bool)
                and reasons (list).
        """
        errors = []
        for key in resourcefiles_mapping.keys():
            if metadata[key] in resourcefiles_mapping[key]['invalid_values'].keys():  # noqa
                errors.append({
                    'key': key,
                    'error_msg': resourcefiles_mapping[key]['invalid_values'][metadata[key]],   # noqa pylint: disable=C0301
                })

        if len(errors) == 0:
            return True, []
        return False, errors

    def validate_proxy_bundles(self, export_dir):
        """Validates proxy bundles.

        Args:
            export_dir (str): Directory containing
                proxy bundles.

        Returns:
            dict: Validation results for APIs and
                sharedflows.
        """
        apis = self.xorhybrid.list_org_objects('apis')
        sharedflows = self.xorhybrid.list_org_objects('sharedflows')
        apis_sf_list = {'apis': apis, 'sharedflows': sharedflows}
        validation = {'apis': [], 'sharedflows': []}
        for each_api_type in ['apis', 'sharedflows']:
            bundle_dir = f"{export_dir}/{each_api_type}"
            for proxy_bundle in list_dir(bundle_dir):
                each_validation = self.validate_proxy(bundle_dir, each_api_type, proxy_bundle)    # noqa pylint: disable=C0301
                api_name = proxy_bundle.split(".zip")[0]
                if api_name in apis_sf_list[each_api_type]:
                    each_validation['imported'] = True
                else:
                    each_validation['imported'] = False
                validation[each_api_type].append(each_validation)
        return validation

    @retry()
    def validate_proxy(self, export_dir, each_api_type, proxy_bundle):
        """Validates a single proxy bundle.

        Args:
            export_dir (str): Directory containing
                proxy bundles.
            each_api_type (str): Type of proxy ('apis' or
                'sharedflows').
            proxy_bundle (str): Proxy bundle filename.

        Returns:
            dict: Validation result for the proxy.
        """
        api_name = proxy_bundle.split(".zip")[0]
        validation_response = self.xorhybrid.create_api(
                                each_api_type,
                                api_name,
                                f"{export_dir}/{proxy_bundle}",
                                'validate'
                            )
        obj = copy.copy(validation_response)
        if 'error' in validation_response:
            obj['name'] = api_name
            obj['importable'], obj['reason'] = False,validation_response['error'].get('details','ERROR')   # noqa pylint: disable=C0301
        else:
            obj['importable'], obj['reason'] = True, []
        return obj

    def validate_env_flowhooks(self, env, flowhooks):
        """Validates environment flowhooks.

        Args:
            env (str): Environment name.
            flowhooks (dict): Flowhook configurations.

        Returns:
            list: Validated flowhooks with
                importability status and reasons.
        """
        validation_flowhooks = []
        for flowhook in flowhooks.keys():
            obj = copy.copy(flowhooks[flowhook])
            obj['name'] = flowhook
            obj['importable'], obj['reason'] = self.validate_env_flowhooks_resource(env, flowhooks[flowhook])   # noqa pylint: disable=C0301
            validation_flowhooks.append(obj)
        return validation_flowhooks

    def validate_env_flowhooks_resource(self, env, flowhook):
        """Validates a single flowhook resource.

        Args:
            env (str): Environment name.
            flowhook (dict): Flowhook configuration.

        Returns:
            tuple: Importability (bool) and
                reasons (list).
        """
        errors = []
        if "sharedFlow" in flowhook:
            env_sf_deployment = self.xorhybrid.get_env_object(env, "sharedflows", flowhook["sharedFlow"]+"/deployments")   # noqa pylint: disable=C0301
            if "deployments" in env_sf_deployment and len(env_sf_deployment["deployments"]) == 0:   # noqa pylint: disable=C0301
                errors.append({
                    'key': "sharedFlow",
                    'error_msg': f"Flowhook sharedflow - {flowhook['sharedFlow']} is not present in APIGEE X environment {env}",   # noqa pylint: disable=C0301
                })

        if len(errors) == 0:
            return True, []
        return False, errors
