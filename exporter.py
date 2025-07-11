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

"""Exports Apigee Edge configuration data.

This module provides functionality to export various components
of a classic Apigee Edge organization, including:

- Environments and their configurations (target servers, KVMs,
    references, resource files, keystores, flow hooks, caches).
- Organization-level objects (KVMs, developers, API products,
    companies, apps, resource files).
- API proxy bundles and metadata (revisions, deployments).
- Virtual hosts.

It uses the Apigee Management API to retrieve configuration details
and stores them in a structured format.  The module supports
exporting data to JSON files and also provides a mechanism to
reconstruct the configuration from the exported data.  It also
offers methods to fetch dependency data, such as references.
"""

import os
import json
from classic import ApigeeClassic
from utils import parse_config # Added for backend.properties access
from nextgen import ApigeeNewGen
from utils import create_dir, run_parallel, write_file, write_json
from base_logger import logger


class ApigeeExporter():  # pylint: disable=R0902
    """Exports Apigee Edge configuration data.

    This class provides methods to export various components of an Apigee
    Edge organization, including environments, virtual hosts, environment-
    and organization-level objects (KVMs, target servers, resource files,
    etc.), API proxies, and shared flows. It uses the Apigee Management
    API to retrieve configuration details and can store them in a
    structured format, suitable for migration or backup purposes.
    It supports JSON export and can also reconstruct the configuration
    from the exported data.

    Attributes:
        baseurl (str): The base URL of the Apigee Management API.
        org (str): The name of the Apigee organization.
        token (str): The authentication token for the
                        Apigee Management API.
        auth_type (str): The authentication type.
        opdk (ApigeeClassic): An instance of the ApigeeClassic client.
        env_object_types (dict): Mapping of environment object types.
        org_object_types (dict): Mapping of organization object types.
        export_data (dict): A dictionary to store the exported data.
    """

    def __init__(self, baseurl, org, token, auth_type, ssl_verify):  # noqa pylint: disable=R0902,R0917,R0913
        self.baseurl = baseurl
        self.org = org
        self.token = token
        self.auth_type = auth_type
        self.apigee = (ApigeeNewGen(baseurl, org, token,
                       'ENVIRONMENT_TYPE_UNSPECIFIED')
                       if 'apigee.googleapis.com' in baseurl else
                       ApigeeClassic(baseurl, org, token,
                       self.auth_type, ssl_verify=ssl_verify))
        self.apigee_type = ('x' if 'apigee.googleapis.com' in baseurl
                            else 'edge')
        self.env_object_types = {
            'targetservers': 'targetServers',
            'keyvaluemaps': 'kvms',
            'references': 'references',
            'resourcefiles': 'resourcefiles',
            'keystores': 'keystores',
            'flowhooks': 'flowhooks',
            'caches': 'caches'
        } # Note: 'api_traffic' will be handled separately, not as a generic env_object_type
          # as it requires specific analytics API calls.
        self.org_object_types = {
            'org_keyvaluemaps': 'kvms',
            'developers': 'developers',
            'apiproducts': 'apiProducts',
            'companies': 'companies',
            'apps': 'apps',
            'resourcefiles': 'resourcefiles',
        }
        self.unsupported_x_objects = ['resourcefiles', 'companies']
        self.export_data = {
            'orgConfig': {},
            'envConfig': {}
        }

    def export_env(self):
        """Exports Apigee environments.

        Retrieves a list of environments from the Apigee organization and
        initializes the export_data dictionary to store
        environment-specific configurations.
        """
        logger.info("--Exporting environments--")
        envs = self.apigee.list_environments()

        for env in envs:
            self.export_data['envConfig'][env] = {}

    def export_vhosts(self):
        """Exports virtual hosts for each environment.

        Iterates through the exported environments and retrieves
        the virtual hosts configured for each environment.
        Stores the virtual host configuration in the
        export_data dictionary.
        """
        if self.apigee_type == 'x':
            env_groups = self.apigee.list_env_groups()
            self.export_data['orgConfig']['envgroups'] = env_groups
        else:
            envs = self.export_data['envConfig'].keys()
            for env in envs:
                self.export_data['envConfig'][env]['vhosts'] = {}
                vhosts = self.apigee.list_env_vhosts(env)
                for vhost in vhosts:
                    vhost_data = self.apigee.get_env_vhost(env, vhost)
                    self.export_data['envConfig'][env]['vhosts'][vhost] = vhost_data  # noqa

    def export_env_objects(self, env_objects_keys, export_dir):    # noqa pylint: disable=R0912
        """Exports environment-level objects.

        Retrieves and exports various environment-level objects based
        on the provided keys.  Handles special cases for resource files
        and keystores, saving them to specific directories. Stores the
        object data in the export_data dictionary.

        Args:
            env_objects_keys (list): A list of environment object
                                        types to export.
            export_dir (str): The directory to export files to.
        """
        for env in self.export_data.get('envConfig', {}):    # noqa pylint: disable=R1702
            for each_env_object_type in env_objects_keys:
                env_objects = self.apigee.list_env_objects(
                    env, each_env_object_type)
                if each_env_object_type == 'resourcefiles':
                    logger.info("--Exporting Resourcefiles--")
                    if self.apigee_type == 'x' and len(env_objects) == 0:
                        env_objects['resourceFile'] = []
                    env_objects = env_objects['resourceFile']
                    for each_env_object in env_objects:
                        logger.info(      # noqa pylint: disable=W1203
                            f"Exporting Resourcefile {each_env_object['name']}")  # noqa
                        create_dir(
                            f"{export_dir}/resourceFiles/{each_env_object['type']}")    # noqa pylint: disable=W1203
                        obj_data = self.apigee.get_env_object(
                            env, each_env_object_type, each_env_object)
                        obj_data = (obj_data if isinstance(obj_data, bytes)
                                    else obj_data.encode('utf-8'))
                        write_file(
                            f"{export_dir}/resourceFiles/{each_env_object['type']}/{each_env_object['name']}", obj_data)  # noqa pylint: disable=C0301
                        self.export_data['envConfig'][env][self.env_object_types[each_env_object_type]][each_env_object['name']] = {  # noqa pylint: disable=C0301
                            'name': each_env_object['name'],
                            'type': each_env_object['type'],
                            'file': f"{export_dir}/resourceFiles/{each_env_object['type']}/{each_env_object['name']}"  # noqa pylint: disable=C0301
                        }
                elif each_env_object_type == 'keystores':
                    create_dir(f"{export_dir}/keystore_certificates/env-{env}")  # noqa
                    logger.info("--Exporting keystores--")
                    for each_env_object in env_objects:
                        logger.info(f"Exporting keystore {each_env_object}")    # noqa pylint: disable=W1203
                        create_dir(
                            f"{export_dir}/keystore_certificates/env-{env}/{each_env_object}")  # noqa pylint: disable=C0301
                        obj_data = self.apigee.get_env_object(
                            env, each_env_object_type, each_env_object)
                        obj_data['alias_data'] = {}
                        for alias in obj_data.get('aliases', []):
                            if self.apigee_type == 'x':
                                alias_name = alias
                            else:
                                alias_name = alias.get('aliasName')
                            create_dir(
                                f"{export_dir}/keystore_certificates/env-{env}/{each_env_object}/{alias_name}")  # noqa pylint: disable=C0301
                            alias_data = self.apigee.get_env_object(
                                env, f"keystores/{each_env_object}/aliases", alias_name)  # noqa pylint: disable=C0301
                            certificate = self.apigee.get_env_object(
                                env, f"keystores/{each_env_object}/aliases", f"{alias_name}/certificate")  # noqa pylint: disable=C0301
                            with open(f"{export_dir}/keystore_certificates/env-{env}/{each_env_object}/{alias_name}/certificate.pem", "wb") as f:  # noqa pylint: disable=C0301
                                if isinstance(certificate, bytes):
                                    f.write(certificate)
                                else:
                                    f.write(certificate.encode('utf-8'))
                            obj_data['alias_data'][alias_name] = alias_data
                        self.export_data['envConfig'][env][self.env_object_types[each_env_object_type]  # noqa pylint: disable=C0301
                                                           ][each_env_object] = obj_data  # noqa pylint: disable=C0301
                else:
                    logger.info(f"--Exporting {each_env_object_type}--")      # noqa pylint: disable=W1203
                    for each_env_object in env_objects:
                        logger.info(    # noqa pylint: disable=W1203
                            f"Exporting {each_env_object_type} {each_env_object}")  # noqa
                        if self.apigee_type == 'x' and each_env_object_type == 'keyvaluemaps':  # noqa pylint: disable=C0301
                            obj_data = self.apigee.get_env_object(
                                        env, each_env_object_type, f'{each_env_object}/entries')  # noqa pylint: disable=C0301
                        else:
                            obj_data = self.apigee.get_env_object(env, each_env_object_type, each_env_object)  # noqa pylint: disable=C0301
                        self.export_data['envConfig'][env][self.env_object_types[each_env_object_type]  # noqa pylint: disable=C0301
                                                           ][each_env_object] = obj_data  # noqa

    def export_org_objects(self, org_objects_keys):
        """Exports organization-level objects.

        Retrieves and exports various organization-level objects based
        on the provided keys. Handles special cases for resource files
        and KVMs. Stores the object data in the export_data dictionary.

        Args:
            org_objects_keys (list): A list of organization object types
                                        to export.
        """
        for each_org_object_type in org_objects_keys:
            logger.info(f"--Exporting org {each_org_object_type}--")    # noqa pylint: disable=W1203
            self.export_data['orgConfig'][self.org_object_types[each_org_object_type]] = {  # noqa
            }
            if self.apigee_type == 'x' and each_org_object_type in self.unsupported_x_objects:  # noqa pylint: disable
                continue

            if each_org_object_type == 'org_keyvaluemaps':
                each_org_object_type = 'keyvaluemaps'
            org_objects = self.apigee.list_org_objects(each_org_object_type)

            if each_org_object_type == 'resourcefiles':
                org_objects = org_objects['resourceFile']
                for each_org_object in org_objects:
                    logger.info(    # noqa pylint: disable=W1203
                        f"Exporting {each_org_object_type} {each_org_object}")
                    obj_data = self.apigee.get_org_object(
                        each_org_object_type, each_org_object)
                    self.export_data['orgConfig'][self.org_object_types[each_org_object_type]][each_org_object['name']] = {  # noqa pylint: disable=C0301
                        'name': each_org_object['name'],
                        'type': each_org_object['type']
                    }

            elif each_org_object_type == 'keyvaluemaps':
                for each_org_object in org_objects:
                    logger.info(    # noqa pylint: disable=W1203
                        f"Exporting {each_org_object_type} {each_org_object}")
                    if self.apigee_type == 'x':
                        obj_data = self.apigee.get_org_object(
                                    each_org_object_type, f'{each_org_object}/entries')  # noqa pylint: disable=C0301
                    else:
                        obj_data = self.apigee.get_org_object(
                            each_org_object_type, each_org_object)
                    self.export_data['orgConfig'][self.org_object_types['org_keyvaluemaps']  # noqa
                                                  ][each_org_object] = obj_data
            else:
                if each_org_object_type in self.apigee.can_expand:
                    self.export_data['orgConfig'][self.org_object_types[each_org_object_type]  # noqa pylint: disable=C0301
                                                    ] = self.apigee.list_org_objects_expand(each_org_object_type)   # noqa pylint: disable=C0301
                else:
                    for each_org_object in org_objects:
                        logger.info(    # noqa pylint: disable=W1203
                            f"Exporting {each_org_object_type} {each_org_object}")  # noqa
                        obj_data = self.apigee.get_org_object(
                            each_org_object_type, each_org_object)
                        self.export_data['orgConfig'][self.org_object_types[each_org_object_type]][each_org_object] = obj_data  # noqa pylint: disable=C0301

    def developers_list(self):
        """Retrieves a list of developers in the organization.

        Returns:
            dict: A dictionary of developers, keyed by developerId.
        """
        developers = self.apigee.list_org_objects('developers')
        developers_dict = {}
        for developer in developers:
            developer_data = self.apigee.get_org_object('developers',
                                                        developer)
            developers_dict[developer_data['developerId']] = developer
        return developers_dict

    def export_api_metadata(self, api_types):
        """Exports API proxy and shared flow metadata.

        Retrieves revisions and deployment information for APIs and
        shared flows & stores the metadata in the export_data dictionary.

        Args:
            api_types (list): A list of API types ('apis', 'sharedflows').
        """
        for each_api_type in api_types:
            logger.info(f"--Exporting {each_api_type} metadata--")    # noqa pylint: disable=W1203
            apis = self.apigee.list_org_objects(each_api_type)

            for each_api in apis:
                logger.info(f"Exporting {each_api_type} {each_api}")    # noqa pylint: disable=W1203
                # extract revisions
                revs = self.apigee.list_api_revisions(each_api_type, each_api)
                self.export_data['orgConfig'][each_api_type][each_api] = revs

                # extract env level info
                deployments = self.apigee.api_env_mapping(each_api_type, each_api)  # noqa
                for env in deployments['environment']:
                    env_name = env.get('name')
                    revisions = []
                    for revision in env.get('revision'):
                        revisions.append(revision.get('name'))
                    if self.export_data['envConfig'][env_name].get(each_api_type):  # noqa
                        self.export_data['envConfig'][env_name][each_api_type][each_api] = revisions  # noqa pylint: disable=C0301
                    else:
                        self.export_data['envConfig'][env_name][each_api_type] = {}  # noqa
                        self.export_data['envConfig'][env_name][each_api_type][each_api] = revisions  # noqa pylint: disable=C0301

    def export_api_proxy_bundles(self, export_dir, api_types):
        """Exports API proxy and shared flow bundles.

        Downloads and saves the bundles for APIs and shared flows to the
        specified directory.

        Args:
            export_dir (str): The directory to export bundles to.
            api_types (list): A list of API types ('apis', 'sharedflows').
        """
        for each_api_type in api_types:
            logger.info(f"--Exporting {each_api_type} proxy bundle--")    # noqa pylint: disable=W1203
            # apis=self.apigee.list_apis(each_api_type)
            apis = self.export_data['orgConfig'][each_api_type].keys()
            args = (
                (each_api_type, api, f"{export_dir}/{each_api_type}") for api in apis)  # noqa
            run_parallel(self.apigee.fetch_proxy, args)

    def get_export_data(self, resources_list, export_dir):  # noqa pylint: disable=R0912
        """Orchestrates the export process.

        Based on the provided resource list, this method calls the
        appropriate export functions to retrieve and store
        configuration data.

        Args:
            resources_list (list): A list of resources to export.
            export_dir (str): The directory to export data to.

        Returns:
            dict: A dictionary containing the exported configuration data.
        """
        self.export_env()

        for env in self.export_data.get('envConfig', {}):
            self.export_data['envConfig'][env]['vhosts'] = {}
            self.export_data['envConfig'][env]['apis'] = {}
            self.export_data['envConfig'][env]['sharedflows'] = {}
            for _, each_env_object_value in self.env_object_types.items():
                self.export_data['envConfig'][env][each_env_object_value] = {}  # noqa pylint: disable=C0301

        for _, each_org_object_value in self.org_object_types.items():
            self.export_data['orgConfig'][each_org_object_value] = {}
        self.export_data['orgConfig']['apis'] = {}
        self.export_data['orgConfig']['sharedflows'] = {}

        env_objects = []
        org_objects = []
        api_types = []

        if self.apigee_type == 'x':
            self.org_object_types['envgroups'] = 'envgroups'

        if 'all' in resources_list:
            self.export_vhosts()
            for env_object in self.env_object_types:
                env_objects.append(env_object)

            for org_object in self.org_object_types:
                org_objects.append(org_object)

            api_types = ['apis', 'sharedflows']

        else:
            if 'vhosts' in resources_list:
                self.export_vhosts()

            if 'apis' in resources_list:
                api_types.append('apis')
            if 'sharedflows' in resources_list:
                api_types.append('sharedflows')

            for each_resource in resources_list:
                if each_resource in self.env_object_types:
                    env_objects.append(each_resource)

                if each_resource in self.org_object_types:
                    org_objects.append(each_resource)

        self.export_api_metadata(api_types)
        self.export_api_proxy_bundles(export_dir, api_types)

        if len(env_objects) != 0:
            self.export_env_objects(env_objects, export_dir)
        if len(org_objects) != 0:
            self.export_org_objects(org_objects)

        # --- NEW: Handle API Traffic Export ---
        if 'all' in resources_list or 'api_traffic' in resources_list:
            self.export_api_traffic_data()
        # --- END NEW ---

        return self.export_data

    def export_api_traffic_data(self):
        """Exports API proxy traffic data for all environments."""
        logger.info("--Exporting API Proxy Traffic Data--")
        # backend_cfg = parse_config('backend.properties')
        cfg = parse_config('input.properties')
        # time_range = backend_cfg.get('inputs', 'ANALYTICS_TIME_RANGE', fallback='2weeks')

        start_date = cfg.get('inputs', 'ANALYTICS_START_DATE')
        end_date = cfg.get('inputs', 'ANALYTICS_END_DATE')

        for env in self.export_data.get('envConfig', {}):
            if self.apigee_type == 'edge':  # Only for classic Edge
                # Ensure we have the list of deployed APIs for the environment

                # Get traffic data only for proxies that have traffic
                traffic_data_with_hits = self.apigee.get_api_proxy_traffic(env, start_date, end_date)

                # Get all proxies deployed in this environment to ensure we list all of them
                deployed_proxies_in_env = self.export_data.get('envConfig', {}).get(env, {}).get('apis', {}).keys()

                if not deployed_proxies_in_env:
                    self.export_data['envConfig'][env]['api_traffic'] = traffic_data_with_hits
                else:
                    all_proxies_traffic_data = {}
                    for proxy_name in deployed_proxies_in_env:
                        # Check if we have traffic data, otherwise default to 0
                        traffic_info = traffic_data_with_hits.get(proxy_name,
                                                                {'proxy_name': proxy_name, 'total_traffic': 0})
                        all_proxies_traffic_data[proxy_name] = traffic_info

                    self.export_data['envConfig'][env]['api_traffic'] = all_proxies_traffic_data
            else:
                logger.info(f"Skipping API traffic export for Apigee X/Hybrid environment '{env}' as it's not directly supported via this tool's current analytics integration.")

    def create_export_state(self, export_dir):
        """Creates the export state by writing data to JSON files.

        Organizes the exported data and writes it to JSON files in the
        specified directory. Creates separate directories for organization
        and environment configurations.

        Args:
            export_dir (str): The directory to create the export state in.
        """
        create_dir(f"{export_dir}/orgConfig")
        create_dir(f"{export_dir}/envConfig")

        for resource, metadata in self.export_data["orgConfig"].items():
            create_dir(f"{export_dir}/orgConfig/{resource}")
            for res_name, res_metadata in metadata.items():
                write_json(
                    f"{export_dir}/orgConfig/{resource}/{res_name}.json", res_metadata)  # noqa

        for env, env_data in self.export_data["envConfig"].items():
            create_dir(f"{export_dir}/envConfig/{env}")
            for resource, metadata in env_data.items():
                create_dir(f"{export_dir}/envConfig/{env}/{resource}")
                for res_name, res_metadata in metadata.items():
                    write_json(
                        f"{export_dir}/envConfig/{env}/{resource}/{res_name}.json", res_metadata)  # noqa pylint: disable=C0301

    def read_export_state(self, folder_path):
        """Reads the export state from JSON files.

        Reads the previously exported configuration data from JSON files
        in the specified directory.  Reconstructs the data structure
        from the files.

        Args:
            folder_path (str): The path to the directory containing
                                    the export state.

        Returns:
            dict: A dictionary containing the read configuration data.
        """
        export_data = {}
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path):
                if export_data.get(item):
                    export_data[item].append(self.read_export_state(item_path))
                else:
                    export_data[item] = self.read_export_state(item_path)
            else:
                with open(item_path, "r") as json_file:  # noqa pylint: disable=W1514
                    json_content = json.load(json_file)
                    export_data[item[:-5]] = json_content
        return export_data

    def get_dependencies_data(self, dependencies):
        """Retrieves dependency data.

        Fetches data for specified dependencies, such as references,
        and returns it as a dictionary.

        Args:
            dependencies (list): A list of dependencies to retrieve.

        Returns:
            dict: A dictionary containing the dependency data.
        """
        dependencies_data = {}
        for dependency in dependencies:
            dependencies_data[dependency] = {}
            if dependency == 'references':
                envs = self.apigee.list_environments()
                for env in envs:
                    dependencies_data[dependency][env] = {}
                    references = self.apigee.list_env_objects(env, dependency)
                    for reference in references:
                        dependencies_data[dependency][env][reference] = self.apigee.get_env_object(  # noqa pylint: disable=C0301
                            env, dependency, reference)
            else:
                org_objects = self.apigee.list_org_objects(dependency)
                for each_org_object in org_objects:
                    dependencies_data[dependency][each_org_object] = self.apigee.get_org_object(  # noqa pylint: disable=C0301
                        dependency, each_org_object)

        return dependencies_data
