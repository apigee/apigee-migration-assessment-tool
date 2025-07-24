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
import zipfile
import defusedxml.ElementTree as ET  # pylint: disable=E0401

from assessment_mapping.resourcefiles import resourcefiles_mapping
from assessment_mapping.targetservers import targetservers_mapping
from nextgen import ApigeeNewGen
from utils import list_dir, retry


class ApigeeValidator:
    """Validates Apigee artifacts for Apigee X or hybrid.

    Provides methods to validate target servers, resource
    files, proxy bundles, and flow hooks against predefined
    rules and compatibility checks.
    """

    def __init__(
        self,
        baseurl,
        project_id,
        token,
        env_type,
        target_export_data,
        target_compare,
        skip_target_validation=False,
        ssl_verify=True
    ):  # noqa pylint: disable=R0913,W0012,R0917
        """Initializes ApigeeValidator.

        Args:
            project_id (str): The Google Cloud project ID.
            token (str): The OAuth2 access token.
            env_type (str): The Apigee environment type
                ('hybrid' or 'x').
        """
        self.project_id = project_id
        self.target_export_data = target_export_data
        self.target_compare = target_compare
        self.skip_target_validation = skip_target_validation
        if not self.skip_target_validation:
            self.xorhybrid = ApigeeNewGen(baseurl, project_id, token, env_type,
                                          ssl_verify)
        else:
            self.xorhybrid = None

    def validate_org_resource(self, resource_type, resources):
        """Validates environment keyvaluemaps.

        Args:
            env (str): Environment name.
            keyvaluemaps (dict): A dictionary of target
                server configurations.

        Returns:
            list: A list of validated keyvaluemaps
                objects with importability status and
                reasons.
        """
        validation_resources = []
        target_resources = (
            self.target_export_data.get("orgConfig", {}).get(resource_type, {}).keys()  # noqa
        )  # noqa pylint: disable=C0301
        for each_obj, obj in resources.items():
            if resource_type == "developers":
                obj["name"] = each_obj
            obj["importable"], obj["reason"] = True, []
            if not self.target_compare:
                obj["imported"] = "UNKNOWN"
            else:
                if each_obj in target_resources:
                    obj["imported"] = True
                else:
                    obj["imported"] = False
            validation_resources.append(obj)
        return validation_resources

    def validate_kvms(self, env, keyvaluemaps):
        """Validates environment keyvaluemaps.

        Args:
            env (str): Environment name.
            keyvaluemaps (dict): A dictionary of target
                server configurations.

        Returns:
            list: A list of validated keyvaluemaps
                objects with importability status and
                reasons.
        """
        validation_kvms = []
        if env is not None:
            kvms = (
                self.target_export_data.get("envConfig", {})
                .get(env, {})
                .get("kvms", {})
                .keys()
            )  # noqa pylint: disable=C0301
        else:
            kvms = (
                self.target_export_data.get("orgConfig", {}).get("kvms", {}).keys()  # noqa
            )  # noqa pylint: disable=C0301
        for each_kvm, obj in keyvaluemaps.items():
            if "name" not in obj:
                obj["name"] = each_kvm
            obj["importable"], obj["reason"] = True, []
            if not self.target_compare:
                obj["imported"] = "UNKNOWN"
            else:
                if each_kvm in kvms:
                    obj["imported"] = True
                else:
                    obj["imported"] = False
            validation_kvms.append(obj)
        return validation_kvms

    def validate_env_targetservers(self, env, target_servers):
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
        ts = (
            self.target_export_data.get("envConfig", {})
            .get(env, {})
            .get("targetServers", {})
            .keys()
        )  # noqa pylint: disable=C0301
        for _, target_server_data in target_servers.items():
            obj = copy.copy(target_server_data)
            obj["importable"], obj["reason"] = self.validate_env_targetserver_resource(  # noqa
                target_server_data
            )  # noqa pylint: disable=C0301
            if not self.target_compare:
                obj["imported"] = "UNKNOWN"
            else:
                if target_server_data["name"] in ts:
                    obj["imported"] = True
                else:
                    obj["imported"] = False
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
            if (
                targetservers[key]
                in targetservers_mapping[key]["invalid_values"].keys()
            ):  # noqa
                errors.append(
                    {
                        "key": key,
                        "error_msg": targetservers_mapping[key]["invalid_values"][  # noqa
                            targetservers[key]
                        ],  # noqa pylint: disable=C0301
                    }
                )

        if len(errors) == 0:
            return True, []
        return False, errors

    def validate_env_resourcefiles(self, env, resourcefiles):
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
        rf = (
            self.target_export_data.get("envConfig", {})
            .get(env, {})
            .get("resourcefiles", {})
            .keys()
        )  # noqa pylint: disable=C0301
        for resourcefile in resourcefiles.keys():
            obj = copy.copy(resourcefiles[resourcefile])
            obj["importable"], obj["reason"] = self.validate_env_resourcefile_resource(  # noqa
                resourcefiles[resourcefile]
            )  # noqa pylint: disable=C0301
            if not self.target_compare:
                obj["imported"] = "UNKNOWN"
            else:
                if resourcefile in rf:
                    obj["imported"] = True
                else:
                    obj["imported"] = False
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
            if (
                metadata[key] in resourcefiles_mapping[key]["invalid_values"].keys()  # noqa
            ):  # noqa
                errors.append(
                    {
                        "key": key,
                        "error_msg": resourcefiles_mapping[key]["invalid_values"][  # noqa
                            metadata[key]
                        ],  # noqa pylint: disable=C0301
                    }
                )

        if len(errors) == 0:
            return True, []
        return False, errors

    def validate_proxy_bundles(self, export_objects, export_dir, target_export_dir, api_type):  # noqa pylint: disable=C0301
        """Validates proxy bundles.

        Args:
            export_dir (str): Directory containing
                proxy bundles.

        Returns:
            dict: Validation results for APIs and
                sharedflows.
        """
        objects = (
            self.target_export_data.get("orgConfig", {}).get(api_type, {}).keys()  # noqa
        )  # noqa pylint: disable=C0301
        validation = {api_type: []}
        bundle_dir = f"{export_dir}/{api_type}"
        export_bundles = list_dir(bundle_dir)
        for api_name in export_objects:
            proxy_bundle = f"{api_name}.zip"
            if proxy_bundle in export_bundles:
                each_validation = self.validate_proxy(
                    bundle_dir, api_type, proxy_bundle
                )  # noqa pylint: disable=C0301
            else:
                each_validation["name"] = api_name
                each_validation["importable"] = False
                each_validation["reason"] = [
                    {
                        "violations": [
                            "Proxy bundle parse issue OR No valid revisions found"  # noqa
                        ]  # noqa pylint: disable=C0301
                    }
                ]
            if not self.target_compare:
                each_validation["imported"] = "UNKNOWN"
            else:
                if api_name in objects:
                    each_validation["imported"] = True
                    each_comparison = self.compare_proxy(
                        f"{export_dir}/{api_type}/{proxy_bundle}",
                        f"{target_export_dir}/{api_type}/{proxy_bundle}",
                    )
                    each_validation['reason'][0]['violations'].extend(each_comparison)  # noqa
                else:
                    each_validation["imported"] = False
            validation[api_type].append(each_validation)
            each_validation = {}
        return validation

    def compare_proxy(self, source_proxy_bundle: str, target_proxy_bundle: str):  # noqa
        """Validates proxy bundles.

        Args:
            source_proxy_bundle (str): Source proxy bundle.
            target_proxy_bundle (str): Target proxy bundle.

        Returns:
            list: comparison results for API
                    proxy.
        """
        diff = []
        try:
            with zipfile.ZipFile(source_proxy_bundle, "r") as source_zip:
                with zipfile.ZipFile(target_proxy_bundle, "r") as target_zip:
                    source_files = {
                        f.filename for f in source_zip.infolist() if not f.is_dir()  # noqa
                    }
                    target_files = {
                        f.filename for f in target_zip.infolist() if not f.is_dir()  # noqa
                    }
                    for file in source_files:
                        file_dissect = file.split('/')
                        if (file.endswith(".xml") and
                                len(file_dissect) > 2 and
                                file_dissect[1] not in ['manifests']):
                            source_xml = ET.fromstring(source_zip.read(file))
                            if file in target_files:
                                target_xml = ET.fromstring(target_zip.read(file))  # noqa
                                if not self.compare_xml_elements(
                                    source_xml, target_xml
                                ):
                                    diff.append(f"Mismatch in file: {file}")
                            else:
                                diff.append(f"File missing in target: {file}")
        except (zipfile.BadZipFile, FileNotFoundError) as e:
            diff.append(f"Error processing proxy bundles: {e}")
        return diff

    def compare_xml_elements(self, elem1, elem2):
        """Validates proxy bundles.

        Args:
            elem1 (str): Source proxy xml.
            elem2 (str): Target proxy xml.

        Returns:
            bool:
        """
        if elem1.tag != elem2.tag:
            return False
        if elem1.text and elem1.text.strip() != elem2.text and elem2.text.strip():  # noqa
            return False
        if elem1.attrib != elem2.attrib:
            return False
        if len(elem1) != len(elem2):
            return False
        return all(
            self.compare_xml_elements(c1, c2) for c1, c2 in zip(elem1, elem2)
        )

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
        if self.skip_target_validation:
            return {
                "name": api_name,
                "importable": False,
                "reason": [{"violations": ["Validation skipped by user flag."]}],  # noqa
            }

        validation_response = self.xorhybrid.create_api(
            each_api_type, api_name, f"{export_dir}/{proxy_bundle}", "validate"
        )
        obj = copy.copy(validation_response)
        if "error" in validation_response:
            obj["name"] = api_name
            obj["importable"], obj["reason"] = False, validation_response["error"].get(  # noqa
                "details", "ERROR"
            )  # noqa pylint: disable=C0301
        else:
            obj["importable"], obj["reason"] = True, [{"violations": []}]
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
            obj["name"] = flowhook
            obj["importable"], obj["reason"] = self.validate_env_flowhooks_resource(  # noqa
                env, flowhooks[flowhook]
            )  # noqa pylint: disable=C0301
            fh = (
                self.target_export_data.get("envConfig", {})
                .get(env, {})
                .get("flowhooks", {})
                .keys()
            )  # noqa pylint: disable=C0301
            if not self.target_compare:
                obj["imported"] = "UNKNOWN"
            else:
                if flowhook in fh:
                    obj["imported"] = True
                else:
                    obj["imported"] = False
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
        if self.skip_target_validation:
            return False, [
                {"key": "sharedFlow", "error_msg": "Validation skipped by user flag."}  # noqa
            ]
        errors = []
        if "sharedFlow" in flowhook:
            env_sf_deployment = self.xorhybrid.get_env_object(
                env, "sharedflows", flowhook["sharedFlow"] + "/deployments"
            )  # noqa pylint: disable=C0301
            if (
                "deployments" in env_sf_deployment
                and len(env_sf_deployment["deployments"]) == 0
            ):  # noqa pylint: disable=C0301
                errors.append(
                    {
                        "key": "sharedFlow",
                        "error_msg": f"Flowhook sharedflow - {flowhook['sharedFlow']} is not present in APIGEE X environment {env}",  # noqa pylint: disable=C0301
                    }
                )

        if len(errors) == 0:
            return True, []
        return False, errors
