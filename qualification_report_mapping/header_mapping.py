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

"""Loads mappings for the qualification report from JSON files.

This module parses various JSON files containing mappings
and data used to generate the qualification report. The parsed data
is stored in individual variables, making it accessible for
report generation. The `parse_json` utility function is used for
parsing the JSON data.
"""

from utils import parse_json  # pylint: disable=E0401


topology_installation_mapping = parse_json(
    "./qualification_report_mapping_json/topology_installation_mapping.json")
anti_patterns_mapping = parse_json(
    "./qualification_report_mapping_json/anti_patterns.json")
api_limits_mapping = parse_json(
    "./qualification_report_mapping_json/api_limits.json")
api_with_multiple_basepath_mapping = parse_json(
    "./qualification_report_mapping_json/api_with_multiple_basepath.json")
apps_without_api_products_mapping = parse_json(
    "./qualification_report_mapping_json/apps_without_api_products.json")
cache_without_expiry_mapping = parse_json(
    "./qualification_report_mapping_json/cache_without_expiry.json")
cname_anomaly_mapping = parse_json(
    "./qualification_report_mapping_json/cname_anomaly.json")
company_and_developers_mapping = parse_json(
    "./qualification_report_mapping_json/company_and_developers.json")
env_limits_mapping = parse_json(
    "./qualification_report_mapping_json/env_limits.json")
json_path_enabled_mapping = parse_json(
    "./qualification_report_mapping_json/json_path_enabled.json")
northbound_mtls_mapping = parse_json(
    "./qualification_report_mapping_json/northbound_mtls.json")
org_limits_mapping = parse_json(
    "./qualification_report_mapping_json/org_limits.json")
proxies_per_env_mapping = parse_json(
    "./qualification_report_mapping_json/proxies_per_env.json")
unsupported_polices_mapping = parse_json(
    "./qualification_report_mapping_json/unsupported_policies.json")
sharding_output = parse_json(
    "./qualification_report_mapping_json/target_environments.json")
aliases_with_private_keys = parse_json(
    "./qualification_report_mapping_json/aliases_with_private_keys.json")
sharded_proxies = parse_json(
    "./qualification_report_mapping_json/sharded_proxies.json")
org_resourcefiles = parse_json(
    "./qualification_report_mapping_json/org_resourcefiles.json")
api_traffic_mapping = parse_json(
    "./qualification_report_mapping_json/api_traffic.json")
validation_report = parse_json(
    "./qualification_report_mapping_json/validation_report.json")
