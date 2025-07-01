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

"""Interacts with Apigee Edge (Classic) using the Management API.

This module provides a client for interacting with a classic
Apigee Edge organization via its Management API.
It offers methods for retrieving organization details, environments,
various entities (APIs, apps, developers, API products, etc.),
and their configurations. It handles pagination for certain
entity types and allows exporting API proxy bundles.
"""

from requests.utils import quote as urlencode  # pylint: disable=E0401
from rest import RestClient
from base_logger import logger


class ApigeeClassic():
    """A client for interacting with Apigee Edge (Classic)
        via the Management API.

    Provides methods for retrieving organization details, environments,
    various entities (APIs, apps, developers, API products, etc.),
    and their configurations. Handles pagination for certain entity types
    and allows exporting API proxy bundles.
    """

    def __init__(self, baseurl, org, token, auth_type, ssl_verify):  # noqa pylint: disable=R0913,R0917
        self.baseurl = baseurl
        self.org = org
        self.token = token
        self.auth_type = auth_type
        self.client = RestClient(self.auth_type, token, ssl_verify)
        self.requires_pagination = ['apis', 'apps', 'developers',
                                    'apiproducts']
        self.can_expand = {
            'apps': {'expand_key': 'app', 'id': 'appId'},
            'developers': {'expand_key': 'developer', 'id': 'email'},
            'apiproducts': {'expand_key': 'apiProduct', 'id': 'name'}
        }

    def get_org(self):
        """Retrieves details of the Apigee organization.

        Returns:
            dict: A dictionary containing the organization details.
        """
        url = f"{self.baseurl}/organizations/{self.org}"
        org = self.client.get(url)
        return org

    def list_environments(self):
        """Lists all environments in the Apigee organization.

        Returns:
            list: A list of environment names.
        """
        url = f"{self.baseurl}/organizations/{self.org}/environments"
        envs = self.client.get(url)
        return envs

    def list_org_objects(self, org_object):
        """Lists organization-level objects of a specific type.

        Handles pagination for certain object types.

        Args:
            org_object (str): The type of organization object to list
                                (e.g., 'apis', 'apps', 'developers').

        Returns:
            list: A list of organization object names or details,
                    depending on the object type.
        """
        org_objects = []
        object_count = 100
        if org_object in self.requires_pagination:
            start_url = f"{self.baseurl}/organizations/{self.org}/{org_object}?count={object_count}"  # noqa pylint: disable=C0301
            each_org_object = self.client.get(start_url)
            org_objects.extend(each_org_object)
            while len(each_org_object) > 0:
                start_key = each_org_object[-1]
                params = {'startKey': start_key}
                each_org_object = self.client.get(start_url, params=params)
                each_org_object.remove(start_key)
                org_objects.extend(each_org_object)
        else:
            url = f"{self.baseurl}/organizations/{self.org}/{org_object}"
            org_objects = self.client.get(url)
        return org_objects

    def list_org_objects_expand(self, org_object):
        """Lists organization-level objects with expanded details.

        Handles pagination and expands details for supported object types.

        Args:
            org_object (str): The type of organization object to list
                            (e.g., 'apps', 'developers', 'apiproducts').

        Returns:
            dict: A dictionary of organization objects,
                    keyed by their ID, with expanded details.
        """
        org_objects = {}
        object_count = 100
        expand_key = self.can_expand.get(org_object).get('expand_key')
        id_key = self.can_expand.get(org_object).get('id')
        start_url = f"{self.baseurl}/organizations/{self.org}/{org_object}?count={object_count}&expand=true"  # noqa pylint: disable=C0301
        each_org_object = self.client.get(start_url)
        each_org_object = each_org_object.get(expand_key, {})
        for each_item in each_org_object:
            org_objects[each_item[id_key]] = each_item
        while len(each_org_object) > 0:
            start_key = each_org_object[-1].get(id_key)
            params = {'startKey': start_key}
            each_org_object = self.client.get(start_url, params=params)
            each_org_object = each_org_object.get(expand_key, {})
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
            resource_type = org_object_name["type"]
            name = org_object_name["name"]
            url = f"{self.baseurl}/organizations/{self.org}/{org_object}/{resource_type}/{name}"  # noqa pylint: disable=C0301
            data = self.client.get(url)
            return data
        org_object_name = urlencode(org_object_name)
        url = f"{self.baseurl}/organizations/{self.org}/{org_object}/{org_object_name}"  # noqa
        org_object = self.client.get(url)
        return org_object

    def list_env_objects(self, env, env_object):
        """Lists environment-level objects of a specific type.

        Args:
            env (str): The environment name.
            env_object (str): The type of environment object to list
                                (e.g., 'targetservers', 'caches').

        Returns:
            list: A list of environment object names or details.
        """
        url = f"{self.baseurl}/organizations/{self.org}/environments/{env}/{env_object}"  # noqa
        env_objects = self.client.get(url)
        return env_objects

    def get_env_object(self, env, env_object, env_object_name):
        """Retrieves details of a specific environment-level object.

        Args:
            env (str): The environment name.
            env_object (str): The type of environment object
                                (e.g., 'targetservers', 'caches').
            env_object_name (str or dict): The name or identifier
                        (including type for resourcefiles) of the object.

        Returns:
            dict: A dictionary containing the object details.
        """
        if len(env_object_name) == 0:
            return {'name': 'EMPTY_OBJECT_NAME'}
        if env_object == "resourcefiles":
            resource_type = env_object_name["type"]
            name = env_object_name["name"]
            url = f"{self.baseurl}/organizations/{self.org}/environments/{env}/{env_object}/{resource_type}/{name}"  # noqa pylint: disable=C0301
            data = self.client.get(url)
        else:
            env_object_name = urlencode(env_object_name)
            url = f"{self.baseurl}/organizations/{self.org}/environments/{env}/{env_object}/{env_object_name}"  # noqa pylint: disable=C0301
            data = self.client.get(url)
        return data

    def list_env_vhosts(self, env):
        """Lists virtual hosts in a specific environment.

        Args:
            env (str): The environment name.

        Returns:
            list: A list of virtual host names.
        """
        url = f"{self.baseurl}/organizations/{self.org}/environments/{env}/virtualhosts"  # noqa
        env_objects = self.client.get(url)
        return env_objects

    def get_env_vhost(self, env, vhost):
        """Retrieves details of a specific virtual host in an environment.

        Args:
            env (str): The environment name.
            vhost (str): The virtual host name.

        Returns:
            dict: A dictionary containing the virtual host details.
        """
        url = f"{self.baseurl}/organizations/{self.org}/environments/{env}/virtualhosts/{vhost}"  # noqa pylint: disable=C0301
        env_object = self.client.get(url)
        return env_object

    def list_apis(self, api_type):
        """Lists APIs or Sharedflows of a given type.

        Args:
            api_type (str):  The type of API - 'apis' or 'sharedflows'

        Returns:
            list: A list of API or Sharedflow names
        """
        url = f"{self.baseurl}/organizations/{self.org}/{api_type}"
        apis = self.client.get(url)
        return apis

    def list_api_revisions(self, api_type, api_name):
        """Lists revisions of a specific API or Sharedflow.

        Args:
            api_type (str): The type of API - 'apis' or 'sharedflows'.
            api_name (str): The name of the API or Sharedflow.

        Returns:
            list: A list of revision numbers.
        """
        url = f"{self.baseurl}/organizations/{self.org}/{api_type}/{api_name}/revisions"  # noqa
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
        url = f"{self.baseurl}/organizations/{self.org}/{api_type}/{api_name}/deployments"  # noqa
        deployments = self.client.get(url)
        return deployments

    def list_apis_env(self, env_name):
        """Lists APIs deployed in a specific environment.

        Args:
            env_name (str): The environment name.

        Returns:
            list: A list of API names deployed in the environment.
        """
        url = f"{self.baseurl}/organizations/{self.org}/environments/{env_name}/deployments"  # noqa
        deployments = self.client.get(url)
        apis_list = [api["name"] for api in deployments["aPIProxy"]]
        return apis_list

    def fetch_api_revision(self, api_type, api_name, revision, export_dir):
        """Downloads the bundle for a specific API or Sharedflow revision.

        Args:
            api_type (str): The type of API - 'apis' or 'sharedflows'.
            api_name (str): The name of the API or Sharedflow.
            revision (str): The revision number.
            export_dir (str): The directory to save the bundle to.
        """
        url = f"{self.baseurl}/organizations/{self.org}/{api_type}/{api_name}/revisions/{revision}?format=bundle"  # noqa pylint: disable=C0301
        bundle = self.client.file_get(url)
        self.write_proxy_bundle(export_dir, api_name, bundle)

    def write_proxy_bundle(self, export_dir, file_name, data):
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

    def view_pod_component_details(self, pod):
        """Retrieves the details of components within a specific pod.

        Args:
            pod (str): The name of the pod.

        Returns:
            list: A list of dictionaries, each containing
                    details of a component.
        """
        url = f"{self.baseurl}/servers?pod={pod}"
        view_pod_response = self.client.get(url)
        return view_pod_response

    def get_api_proxy_traffic(self, env_name, start_date, end_date):
        """Retrieves API proxy traffic data for a specific environment.

        Args:
            env_name (str): The name of the environment.
            start_date (str): The starting date of the time range (MM/DD/YYYY).
            end_date (str): The ending date of the time range (MM/DD/YYYY)

        Returns:
            dict: A dictionary of traffic data for API proxies, keyed by
                  proxy name. Returns an empty dict if no data or an error
                  occurs.
        """
        logger.info(f"Fetching API proxy traffic for environment '{env_name}' from '{start_date}' to '{end_date}'")
        url = (f"{self.baseurl}/organizations/{self.org}/environments/{env_name}/stats/apiproxy?"
               f"select=sum(message_count)&timeRange={start_date}%2000:00~{end_date}%2023:59&timeUnit=day")

        try:
            traffic_data = self.client.get(url)
            if (traffic_data and 'environments' in traffic_data and traffic_data['environments']):
                proxy_traffic_dict = {}
                for env_data in traffic_data['environments']:
                    for dimension in env_data.get('dimensions', []):
                        proxy_name = dimension.get('name')
                        if not proxy_name:
                            continue
                        total_message_count = 0
                        for metric in dimension.get('metrics', []):
                            if metric.get('name') == 'sum(message_count)':
                                for value_entry in metric.get('values', []):
                                    try:
                                        # Value can be a float string like "7.0"
                                        count = int(float(value_entry.get('value', 0)))
                                        total_message_count += count
                                    except (ValueError, TypeError):
                                        logger.warning(f"Could not parse traffic value for proxy '{proxy_name}': {value_entry.get('value')}")
                        proxy_traffic_dict[proxy_name] = {
                            'proxy_name': proxy_name,
                            'total_traffic': total_message_count
                        }
                return proxy_traffic_dict
            logger.info("No API traffic data returned from the API.")
            return {}
        except Exception as e:
            logger.error(f"Error fetching or parsing API proxy traffic for {env_name}: {e}", exc_info=True)
            return {}
