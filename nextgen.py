#!/usr/bin/python  # noqa pylint: disable=R0801

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

"""Interacts with Apigee X or hybrid using the Management API.

This module provides a client for interacting with Apigee X or hybrid.
It offers methods for creating and validating API proxies and sharedflows.
"""

from requests.utils import quote as urlencode  # pylint: disable=E0401
from google.cloud import resourcemanager_v3  # pylint: disable=E0401
from google.oauth2.credentials import Credentials  # pylint: disable=E0401
from utils import parse_json
from rest import RestClient

class ApigeeNewGen():   # noqa pylint: disable=R0902
    """A client for interacting with Apigee X or hybrid.

    Provides methods to interact with Apigee X or hybrid environments,
    including creating and validating API proxies and shared flows.
    """
    def __init__(self, baseurl, project_id, token, env_type, ssl_verify): # noqa pylint: disable=R0913,R0917
        """Initializes the ApigeeNewGen client.

        Args:
            project_id (str): The Google Cloud project ID.
            token (str): The OAuth2 access token.
            env_type (str): The environment type ('hybrid' or 'x').
                            Defaults to 'ENVIRONMENT_TYPE_UNSPECIFIED'.
        """
        self.baseurl = baseurl
        self.project_id = project_id
        self.token = token
        self.env_type = env_type or 'ENVIRONMENT_TYPE_UNSPECIFIED'
        self.requires_pagination = {
            'apps': {'limit': 'pageSize', 'next_key': 'pageToken'},
            'developers': {'limit': 'count', 'next_key': 'startKey'},
            'apiproducts': {'limit': 'count', 'next_key': 'startKey'},
            }
        self.can_expand = {
            'apis': {'expand_key': 'proxies', 'id': 'name'},
            'apiproducts': {'expand_key': 'apiProduct', 'id': 'name'},
            'sharedflows': {'expand_key': 'sharedFlows', 'id': 'name'},
            'envgroups': {'expand_key': 'environmentGroups', 'id': 'name'},
            'apps': {'expand_key': 'app', 'id': 'appId'},
            'developers': {'expand_key': 'developer', 'id': 'email'},
            'keyvaluemaps': {'expand_key': None, 'id': None},
            'environments': {'expand_key': None, 'id': None},
        }
        self.env_objects = ['keyvaluemaps', 'targetservers', 'flowhooks',
                            'keystores', 'caches']
        self.client = RestClient('oauth', token, ssl_verify)

    def validate_permissions(self):
        """Validate if the user has right permissions.

        Returns:
            array: A array of missing permissions.
        """
        permissions_list = parse_json('permissions.json')
        credentials = Credentials(self.token)
        projects_client = resourcemanager_v3.ProjectsClient(credentials=credentials)  # noqa pylint: disable=C0301
        project_id = f"projects/{self.project_id}"
        owned_permissions = projects_client.test_iam_permissions(
                            resource=project_id,
                            permissions=permissions_list,
                            ).permissions
        absent_permissions = [item for item in permissions_list
                              if item not in owned_permissions]
        return absent_permissions

    def get_org(self):
        """Retrieves details of the Apigee organization.

        Returns:
            dict: A dictionary containing the organization details.
        """
        url = f"{self.baseurl}/organizations/{self.project_id}"
        org = self.client.get(url)
        return org

    def list_environments(self):
        """Lists all environments in the Apigee organization.

        Returns:
            list: A list of environment names.
        """
        return self.list_org_objects('environments')

    def _apigee_object_util(self, org_object, each_org_object_data, expand=False):  # noqa pylint: disable=C0301
        expand_key = self.can_expand.get(org_object).get('expand_key')
        id_key = self.can_expand.get(org_object).get('id')
        objects = []
        if isinstance(each_org_object_data, list):
            objects.extend(each_org_object_data)
        if isinstance(each_org_object_data, dict):
            org_objects_list = each_org_object_data.get(expand_key, [])
            for each_object in org_objects_list:
                if expand:
                    objects.append(each_object)
                else:
                    objects.append(each_object.get(id_key))
        return objects

    def list_org_objects(self, org_object):
        """Retrieves org objects of the Apigee organization.

        Returns:
            list: A list containing the org object details.
        """
        org_objects = []
        object_count = 100
        if org_object in self.requires_pagination:
            next_key = self.requires_pagination.get(org_object).get('next_key')  # noqa
            limit_param = self.requires_pagination.get(org_object).get('limit')  # noqa
            params = {
                limit_param: object_count
            }
            start_url = f"{self.baseurl}/organizations/{self.project_id}/{org_object}"    # noqa
            each_org_object_data = self.client.get(start_url, params=params)
            each_org_object = self._apigee_object_util(org_object, each_org_object_data)  # noqa pylint: disable=C0301
            org_objects.extend(each_org_object)
            while len(each_org_object) > 0:
                start_key = each_org_object[-1]
                params[next_key] = start_key
                each_org_object_data = self.client.get(start_url, params=params)  # noqa pylint: disable=C0301
                each_org_object = self._apigee_object_util(org_object, each_org_object_data)  # noqa pylint: disable=C0301
                each_org_object.remove(start_key)
                org_objects.extend(each_org_object)
        else:
            url = f"{self.baseurl}/organizations/{self.project_id}/{org_object}"  # noqa pylint: disable=C0301
            org_object_data = self.client.get(url)
            org_objects.extend(self._apigee_object_util(org_object, org_object_data))  # noqa pylint: disable=C0301
        return org_objects

    def list_org_objects_expand(self, org_object):
        """Retrieves org objects of the Apigee organization.

        Returns:
            list: A list containing the org object details.
        """
        org_objects = {}
        object_count = 100
        expand_param = ['developers', 'apiproducts']
        next_key = self.requires_pagination.get(org_object, {}).get('next_key', None)  # noqa
        id_key = self.can_expand.get(org_object).get('id')
        limit_key = self.requires_pagination.get(org_object, {}).get('limit', None)  # noqa pylint: disable=C0301
        if next_key is None:
            params = {}
        else:
            params = {
                limit_key: object_count,
            }
        if org_object in expand_param:
            params['expand'] = True
        start_url = f"{self.baseurl}/organizations/{self.project_id}/{org_object}"    # noqa
        each_org_object_data = self.client.get(start_url, params=params)
        each_org_object = self._apigee_object_util(org_object, each_org_object_data, True)    # noqa
        for each_item in each_org_object:
            org_objects[each_item[id_key]] = each_item
        if next_key is None:
            return org_objects
        while len(each_org_object) > 0:
            start_key = each_org_object[-1].get(id_key)    # noqa
            params[next_key] = start_key    # noqa
            each_org_object_data = self.client.get(start_url, params=params)
            each_org_object = self._apigee_object_util(org_object, each_org_object_data, True)       # noqa pylint: disable=C0301
            each_org_object.pop(0)
            for each_item in each_org_object:
                org_objects[each_item[id_key]] = each_item
        return org_objects

    def get_org_object(self, org_object, org_object_name):
        """Retrieves details of a specific organization-level object.

        Args:
            org_object (str): The type of organization object
                                (e.g., 'developers', 'apiproducts').
            org_object_name (str or dict): The name or identifier
                        (including type for resourcefiles) of the object.

        Returns:
            dict: A dictionary containing the object details.
        """
        if len(org_object_name) == 0:
            return {'name': 'EMPTY_OBJECT_NAME'}
        if org_object == "resourcefiles":
            return {}
        org_object_name = urlencode(org_object_name)
        url = f"{self.baseurl}/organizations/{self.project_id}/{org_object}/{org_object_name}"     # noqa pylint: disable=C0301
        org_object = self.client.get(url)
        return org_object

    def list_env_objects(self, env, env_object_type):
        """Retrieves env objects of the Apigee organization.

        Returns:
            list: A list containing the env object details.
        """
        env_objects = []
        url = f"{self.baseurl}/organizations/{self.project_id}/environments/{env}/{env_object_type}"    # noqa pylint: disable=C0301
        env_objects = self.client.get(url)
        return env_objects

    def get_env_object(self, env, env_object, env_object_name):
        """Retrieves an environment-level object.

        Args:
            env (str): The environment name.
            env_object (str): The object type (e.g., 'resourcefiles').
            env_object_name (str or dict): The object name or identifier.

        Returns:
            dict: The environment object details.
        """
        if len(env_object_name) == 0:
            return {'name': 'EMPTY_OBJECT_NAME'}
        if env_object == 'resourcefiles':
            url = f"{self.baseurl}/organizations/{self.project_id}/environments/{env}/{env_object}/{env_object_name['type']}/{env_object_name['name']}"   # noqa pylint: disable=C0301
            env_object = self.client.get(url)
        else:
            url = f"{self.baseurl}/organizations/{self.project_id}/environments/{env}/{env_object}/{env_object_name}"    # noqa pylint: disable=C0301
            env_object = self.client.get(url)
        return env_object

    def list_env_groups(self):
        """Lists virtual hosts in a specific environment.

        Args:
            env (str): The environment name.

        Returns:
            list: A list of virtual host names.
        """
        envgroups = self.list_org_objects_expand('envgroups')
        return envgroups

    def get_env_groups(self, env_group):
        """Retrieves details of a specific virtual host in an environment.

        Args:
            env (str): The environment name.
            env_group (str): The virtual host name.

        Returns:
            dict: A dictionary containing the virtual host details.
        """
        env_group = self.get_org_object('envgroups', env_group)
        return env_group

    def list_apis(self, api_type):
        """Lists APIs or Sharedflows of a given type.

        Args:
            api_type (str):  The type of API - 'apis' or 'sharedflows'

        Returns:
            list: A list of API or Sharedflow names
        """
        if api_type not in ['apis', 'sharedflows']:
            return []
        apis = self.list_org_objects(api_type)
        return apis

    def list_api_revisions(self, api_type, api_name):
        """Lists revisions of a specific API or Sharedflow.

        Args:
            api_type (str): The type of API - 'apis' or 'sharedflows'.
            api_name (str): The name of the API or Sharedflow.

        Returns:
            list: A list of revision numbers.
        """
        url = f"{self.baseurl}/organizations/{self.project_id}/{api_type}/{api_name}/revisions"     # noqa pylint: disable=C0301
        revisions = self.client.get(url)
        return revisions

    def api_env_mapping(self, api_type, api_name):
        """Retrieves the environment deployment mapping for an API
            or Sharedflow.

        Args:
            api_type (str): The type of API - 'apis' or 'sharedflows'.
            api_name (str): The name of the API or Sharedflow.

        Returns:
            dict: A dictionary containing the deployment mapping.
        """
        url = f"{self.baseurl}/organizations/{self.project_id}/{api_type}/{api_name}/deployments"     # noqa pylint: disable=C0301
        deployments_data = self.client.get(url)
        if len(deployments_data) == 0:
            return {'environment': []}
        formatted_deployments = []
        for dep in deployments_data.get('deployments'):
            formatted_deployments.append({
                'name': dep.get('environment'),
                'revision': [{'name': dep.get('revision')}]
            })
        return {'environment': formatted_deployments}

    def list_apis_env(self, env_name):
        """Lists APIs deployed in a specific environment.

        Args:
            env_name (str): The environment name.

        Returns:
            list: A list of API names deployed in the environment.
        """
        url = f"{self.baseurl}/organizations/{self.project_id}/environments/{env_name}/deployments"     # noqa pylint: disable=C0301
        deployments_data = self.client.get(url)
        deployments = deployments_data.get('deployments')
        apis_list = [api.get('apiProxy') for api in deployments]
        return apis_list

    def fetch_api_revision(self, api_type, api_name, revision, export_dir):
        """Downloads the bundle for a specific API or Sharedflow revision.

        Args:
            api_type (str): The type of API - 'apis' or 'sharedflows'.
            api_name (str): The name of the API or Sharedflow.
            revision (str): The revision number.
            export_dir (str): The directory to save the bundle to.
        """
        url = f"{self.baseurl}/organizations/{self.project_id}/{api_type}/{api_name}/revisions/{revision}?format=bundle"  # noqa pylint: disable=C0301
        bundle = self.client.file_get(url)
        self._write_proxy_bundle(export_dir, api_name, bundle)

    def _write_proxy_bundle(self, export_dir, file_name, data):
        """Writes a proxy bundle to a file.

        Args:
            export_dir (str): The directory to write the file to.
            file_name (str): The name of the file.
            data (bytes): The bundle data.
        """
        file_path = f"./{export_dir}/{file_name}.zip"
        with open(file_path, 'wb') as fl:
            fl.write(data)

    def fetch_proxy(self, arg_tuple):
        """Fetches the latest revision of an API proxy bundle.

        Args:
            arg_tuple (tuple): A tuple containing
                (api_type, api_name, export_dir).
        """
        revisions = self.list_api_revisions(arg_tuple[0], arg_tuple[1])
        if len(revisions) > 0:
            self.fetch_api_revision(
                arg_tuple[0], arg_tuple[1], revisions[-1], arg_tuple[2])

    def create_api(self, api_type, api_name, proxy_bundle_path, action):
        """Creates or validates an API proxy or sharedflow.

        Args:
            api_type (str): The type ('apis' or 'sharedflows').
            api_name (str): The name of the proxy/flow.
            proxy_bundle_path (str): Path to the proxy/flow bundle.
            action (str): The action ('create' or 'validate').

        Returns:
            dict: The API creation/validation response.

        """
        url = f"{self.baseurl}/organizations/{self.project_id}/{api_type}?name={api_name}"   # noqa pylint: disable=C0301
        params = {
            'action': action,
            'validate': True
        }
        files = [
            ('data', (api_name, open(proxy_bundle_path, 'rb'), 'application/zip'))   # noqa pylint: disable=C0301,R1732
        ]
        api_object = self.client.file_post(url, params, None, files)
        return api_object
