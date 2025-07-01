#!/usr/bin/python  # noqa pylint: disable=C0302

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

"""Generates an Excel workbook containing a detailed qualification report
for Apigee migration assessment.
"""

import json
import xlsxwriter  # pylint: disable=E0401
from qualification_report_mapping.header_mapping import (
    topology_installation_mapping, proxies_per_env_mapping,
    northbound_mtls_mapping, company_and_developers_mapping,
    anti_patterns_mapping, cache_without_expiry_mapping,
    apps_without_api_products_mapping, json_path_enabled_mapping,
    cname_anomaly_mapping, unsupported_polices_mapping,
    api_limits_mapping,
    org_limits_mapping,
    env_limits_mapping,
    api_with_multiple_basepath_mapping,
    sharding_output,
    aliases_with_private_keys,
    sharded_proxies,
    org_resourcefiles,
    api_traffic_mapping, # New import
    validation_report,
)
from qualification_report_mapping.report_summary import report_summary
from base_logger import logger


class QualificationReport():  # noqa pylint: disable=R0902,R0904
    """Generates an Excel qualification report for Apigee migration assessment.

    This class creates an Excel workbook with multiple sheets, each presenting
    specific data related to the Apigee environment being assessed.  The report
    covers various aspects like proxy counts, security settings, resource
    limits, potential issues, and topology information.
    """

    def __init__(self, workbookname, export_data,  # noqa pylint: disable=R0913,R0917
                 topology_mapping, cfg, backend_cfg, org_name):
        """Initializes the QualificationReport object.

        Args:
            workbookname (str): The name of the Excel workbook to be
                                created.
            export_data (dict): A dictionary containing the exported
                                Apigee data.
            topology_mapping (dict): A dictionary containing the
                                topology mapping.
            cfg (configparser.ConfigParser): The configuration object.
            backend_cfg (configparser.ConfigParser): Backend
                                configurations.
            org_name (str): The name of the Apigee organization.
        """
        self.workbook = xlsxwriter.Workbook(workbookname)
        self.export_data = export_data
        self.topology_mapping = topology_mapping
        self.org_name = org_name
        self.cfg = cfg
        self.backend_cfg = backend_cfg
        # Heading formats
        self.heading_format = self.workbook.add_format(
            {'bold': True, 'bg_color': '#ADD8E6', 'font_color': 'white'})

        # Format to represent resource migration status
        self.danger_format = self.workbook.add_format({'bg_color': '#f5cbcc'})
        self.yellow_format = self.workbook.add_format({'bg_color': 'yellow'})
        self.green_format = self.workbook.add_format({'bg_color': '#5fbd76'})

        # Information blue box formats
        self.info_format = self.workbook.add_format(
            {'bg_color': '#4285f4', 'font_color': 'white',
             'border': 1, 'text_wrap': True, 'font_size': 12,
             'valign': 'top'})
        self.info_bold_format = self.workbook.add_format(
            {'bg_color': '#4285f4', 'font_color': 'white',
             'border': 1, 'text_wrap': True, 'bold': True,
             'font_size': 18})
        self.info_italic_underline_format = self.workbook.add_format(
            {'bg_color': '#4285f4', 'font_color': 'white',
             'border': 1, 'text_wrap': True, 'italic': True,
             'underline': True, 'font_size': 14})
        self.info_bold_underline_format = self.workbook.add_format(
            {'bg_color': '#4285f4', 'font_color': 'white', 'border': 1,
             'text_wrap': True, 'bold': True, 'underline': True,
             'font_size': 14})
        self.ref_link_heading_format = self.workbook.add_format(
            {'border': 1, 'text_wrap': True, 'bold': True,
             'underline': True, 'font_size': 14})
        self.ref_link_format = self.workbook.add_format(
            {'border': 1, 'text_wrap': True, 'bold': False,
             'underline': True, 'font_size': 12, 'font_color': 'blue'})

        # Qualification Report Summary
        self.summary_main_header_format = self.workbook.add_format(
            {'bg_color': '#4285f4', 'font_color': 'white', 'border': 1,
             'text_wrap': True, 'bold': True, 'font_size': 24,
             'valign': 'center'})
        self.summary_block_header_format = self.workbook.add_format(
            {'bg_color': '#000000', 'font_color': 'white', 'border': 1,
             'text_wrap': True, 'font_size': 18, 'valign': 'center'})
        self.summary_link_format = self.workbook.add_format(
            {'border': 1, 'text_wrap': True, 'underline': True,
             'font_size': 16, 'font_color': 'blue'})
        self.summary_format = self.workbook.add_format(
            {'border': 1, 'text_wrap': True, 'font_size': 16,
             'font_color': 'black'})
        self.summary_note_blue_format = self.workbook.add_format(
            {'border': 1, 'text_wrap': True, 'font_size': 13,
             'font_color': 'blue', 'valign': 'center',
             "align": "center"})
        self.summary_note_green_format = self.workbook.add_format(
            {'border': 1, 'text_wrap': True, 'font_size': 13,
             'font_color': 'green', 'valign': 'center',
             "align": "center"})
        self.summary_cell_danger_format = self.workbook.add_format(
            {'bg_color': '#f5cbcc', 'valign': 'vcenter',
             "align": "center", 'border': 1, 'text_wrap': True,
             'font_size': 16})
        self.summary_cell_green_format = self.workbook.add_format(
            {'bg_color': '#5fbd76', 'valign': 'vcenter',
             "align": "center", 'border': 1, 'text_wrap': True,
             'font_size': 16})

    # Sheet column heading
    def qualification_report_heading(self, headers, sheet):
        """Writes column headings to a given worksheet.

        Args:
            headers (list): A list of strings representing the
                            column headers.
            sheet (xlsxwriter.Worksheet): The worksheet object
                            to write to.
        """
        # Headings
        col = 0
        alph = 65
        for val in headers:
            sheet.write(f'{chr(alph)}1', val, self.heading_format)
            sheet.set_column(col, col, len(val) + 1)
            col = col+1
            alph = alph+1

    # Get final information box text
    def get_final_info_text_and_format_arr(self, full_text):
        """Formats the information box text with appropriate formatting
                    codes.

        Args:
            full_text (str): The input text string containing formatting
                                tags.

        Returns:
            list: A list of alternating format objects and text
                                strings.
        """
        final_text = []
        for line in full_text.split('\n'):
            if line.startswith("<b>"):
                final_text.append(self.info_bold_format)
                final_text.append(line.split("<b>")[1]+'\n')
            elif line.startswith("<iu>"):
                final_text.append(self.info_italic_underline_format)
                final_text.append(line.split("<iu>")[1]+'\n')
            elif line.startswith("<bu>"):
                final_text.append(self.info_bold_underline_format)
                final_text.append(line.split("<bu>")[1]+'\n')
            else:
                final_text.append(self.info_format)
                final_text.append(line+'\n')

        final_text.append(self.info_format)

        return final_text

    def qualification_report_info_box(self, mapping_json, sheet):
        """Creates an information box within the specified sheet.

        Args:
            mapping_json (dict):  Configuration for the information box.
            sheet (xlsxwriter.Worksheet): The worksheet object to add
                                            the box to.
        """
        # Information box
        alph = 65 + len(mapping_json["headers"])

        if isinstance(mapping_json["info_block"], dict):
            sheet.set_column(len(mapping_json["headers"]), len(mapping_json["headers"])+int(mapping_json["info_block"]["col_merge"]), len(   # noqa pylint: disable=C0301
                mapping_json["info_block"]["text"].split("\n")[int(mapping_json["info_block"]["text_line_no_for_col_count"])]) / int(mapping_json["info_block"]["col_merge"]))   # noqa pylint: disable=C0301

            final_text = self.get_final_info_text_and_format_arr(
                mapping_json["info_block"]["text"])

            sheet.merge_range(
                f'{chr(alph)}{int(mapping_json["info_block"]["start_row"])}:{chr(alph+(int(mapping_json["info_block"]["col_merge"])-1))}{int(mapping_json["info_block"]["end_row"])}', "", self.info_format)   # noqa pylint: disable=C0301
            sheet.write_rich_string(
                f'{chr(alph)}{int(mapping_json["info_block"]["start_row"])}', *final_text)   # noqa pylint: disable=C0301

        elif isinstance(mapping_json["info_block"], list):
            for block in mapping_json["info_block"]:
                if "text_line_no_for_col_count" in block:
                    sheet.set_column(len(mapping_json["headers"]), len(mapping_json["headers"])+int(block["col_merge"]), len(   # noqa pylint: disable=C0301
                        block["text"].split("\n")[int(block["text_line_no_for_col_count"])]) / int(block["col_merge"]))   # noqa pylint: disable=C0301

                final_text = self.get_final_info_text_and_format_arr(
                    block["text"])

                sheet.merge_range(
                    f'{chr(alph)}{int(block["start_row"])}:{chr(alph+(int(block["col_merge"])-1))}{int(block["end_row"])}', "", self.info_format)   # noqa pylint: disable=C0301
                sheet.write_rich_string(
                    f'{chr(alph)}{int(block["start_row"])}', *final_text)

        link_start_row = (int(mapping_json["info_block"]["end_row"])+2 if isinstance(mapping_json["info_block"], dict)   # noqa pylint: disable=C0301
                            else mapping_json["info_block"][len(mapping_json["info_block"])-1]["end_row"]+2)   # noqa pylint: disable=C0301

        if ("link" in mapping_json["info_block"] or "link" in mapping_json):   # noqa pylint: disable=C0301

            link_arr = mapping_json["info_block"]["link"] if isinstance(   # noqa pylint: disable=C0301
                    mapping_json["info_block"], dict) else mapping_json["link"]   # noqa pylint: disable=C0301

            sheet.write_string(f'{chr(alph)}{int(link_start_row)}',
                               f"Reference Link{'s:' if len(link_arr) > 1 else ':'}", self.ref_link_heading_format)   # noqa pylint: disable=C0301
            link_start_row = link_start_row+1

            for link_item in link_arr:
                sheet.write_url(f'{chr(alph)}{link_start_row}',
                                link_item["link"], self.ref_link_format, string=link_item["link_text"])   # noqa pylint: disable=C0301
                link_start_row = link_start_row+1

    def report_proxies_per_env(self):
        """Generates the "Proxies Per Env" report sheet."""

        # Worksheet 1 - [Proxies Per Env]
        logger.info(
            '------------------- Proxies Per Env -----------------------')
        proxies_per_env_sheet = self.workbook.add_worksheet(
            name='Proxies Per Env')

        # Headings
        self.qualification_report_heading(
            proxies_per_env_mapping["headers"], proxies_per_env_sheet)

        env_config = self.export_data.get('envConfig')
        row = 1

        allowed_no_of_proxies_per_env = self.backend_cfg.get(
            'inputs', 'NO_OF_PROXIES_PER_ENV_LIMITS')
        allowed_no_of_shared_flows_per_env = self.backend_cfg.get(
            'inputs', 'NO_OF_SHARED_FLOWS_PER_ENV_LIMITS')
        allowed_no_of_proxies_and_shared_flows_per_env = self.backend_cfg.get(
            'inputs', 'NO_OF_PROXIES_AND_SHARED_FLOWS_PER_ENV_LIMITS')

        for key, value in env_config.items():
            # Org name
            col = 0
            proxies_per_env_sheet.write(row, col, self.org_name)
            # Env name
            col += 1
            proxies_per_env_sheet.write(row, col, key)
            # No of Proxies
            col += 1
            num_proxies = len(value['apis'])
            if num_proxies > int(allowed_no_of_proxies_per_env):
                proxies_per_env_sheet.write(
                    row, col, num_proxies, self.danger_format)
            else:
                proxies_per_env_sheet.write(row, col, num_proxies)
            # No of Sharedflows
            col += 1
            num_sf = len(value['sharedflows'])
            if num_sf > int(allowed_no_of_shared_flows_per_env):
                proxies_per_env_sheet.write(
                    row, col, num_sf, self.danger_format)
            else:
                proxies_per_env_sheet.write(row, col, num_sf)
            # Total no of Proxies & Sharedflows
            col += 1
            total_api_sf = num_proxies + num_sf
            if total_api_sf > int(allowed_no_of_proxies_and_shared_flows_per_env):   # noqa pylint: disable=C0301
                proxies_per_env_sheet.write(
                    row, col, total_api_sf, self.danger_format)
            else:
                proxies_per_env_sheet.write(
                    row, col, total_api_sf)
            row += 1

        proxies_per_env_sheet.autofit()
        # Info block
        self.qualification_report_info_box(
            proxies_per_env_mapping, proxies_per_env_sheet)

    def report_north_bound_mtls(self):
        """Generates the "Northbound mTLS" report sheet."""
        # Worksheet 3 - [Northbound mTLS]
        logger.info(
            '------------------- Northbound mTLS -----------------------')
        nb_mtls_sheet = self.workbook.add_worksheet(
            name='Northbound mTLS')

        # Headings
        self.qualification_report_heading(
            northbound_mtls_mapping["headers"], nb_mtls_sheet)

        env_config = self.export_data.get('envConfig')
        row = 1

        for env, value in env_config.items():
            vhosts = value['vhosts']
            for vhost, vhost_content in vhosts.items():
                # org name
                col = 0
                nb_mtls_sheet.write(row, col, self.org_name)
                # Env name
                col += 1
                nb_mtls_sheet.write(row, col, env)
                col += 1
                nb_mtls_sheet.write(row, col, vhost)

                if vhost_content.get('sSLInfo'):
                    sslinfo = vhost_content['sSLInfo']
                    col += 1
                    nb_mtls_sheet.write(
                        row, col, sslinfo['enabled'], self.danger_format)
                    col += 1
                    nb_mtls_sheet.write(
                        row, col, sslinfo['clientAuthEnabled'],
                        self.danger_format)
                    col += 1
                    if sslinfo.get('keyStore'):
                        nb_mtls_sheet.write(
                            row, col, sslinfo['keyStore'],
                            self.danger_format)
                    elif vhost_content.get("useBuiltInFreeTrialCert") is True:
                        nb_mtls_sheet.write(
                            row, col, "Free Trial Cert Used",
                            self.danger_format)

                else:
                    col += 1
                    nb_mtls_sheet.write(row, col, 'False')
                row += 1

        nb_mtls_sheet.autofit()
        # Info block
        self.qualification_report_info_box(
            northbound_mtls_mapping, nb_mtls_sheet)

    def report_company_and_developer(self):
        """Generates the "Company And Developers" report sheet."""

        # Worksheet 4 - [Company And Developers]
        logger.info(
            '------------------- Company And Developers -----------------------')   # noqa pylint: disable=C0301
        companies_developers = self.workbook.add_worksheet(
            name='Company And Developers')

        # Headings
        self.qualification_report_heading(
            company_and_developers_mapping["headers"], companies_developers)   # noqa pylint: disable=C0301

        org_config = self.export_data.get('orgConfig')
        companies = org_config['companies']
        row = 1

        # Org name
        for company in companies:
            col = 0
            companies_developers.write(row, col, self.org_name)
            col += 1
            companies_developers.write(row, col, company)
            row += 1

        companies_developers.autofit()
        # Info block
        self.qualification_report_info_box(
            company_and_developers_mapping, companies_developers)

    def report_anti_patterns(self):
        """Generates the "Anti Patterns" report sheet."""
        # Worksheet 5 - [Anti Patterns]
        logger.info('------------------- Anti Patterns -----------------------')   # noqa pylint: disable=C0301
        anti_patterns_sheet = self.workbook.add_worksheet(name='Anti Patterns')

        # Headings
        self.qualification_report_heading(
            anti_patterns_mapping["headers"], anti_patterns_sheet)

        row = 1

        proxy_map = self.export_data['proxy_dependency_map']
        for proxy, values in proxy_map.items():
            if values.get("unifier_created"):
                continue

            anti_pattern_quota = values.get('qualification', {}).get('AntiPatternQuota', {})   # noqa pylint: disable=C0301
            for policy, value in anti_pattern_quota.items():
                col = 0
                anti_patterns_sheet.write(row, col, self.org_name)
                col += 1
                anti_patterns_sheet.write(row, col, proxy)
                col += 1
                anti_patterns_sheet.write(row, col, policy)
                col += 1
                anti_patterns_sheet.write(row, col, value['distributed'])
                col += 1
                anti_patterns_sheet.write(row, col, value['Synchronous'])

                row += 1

        anti_patterns_sheet.autofit()
        # Info block
        self.qualification_report_info_box(
            anti_patterns_mapping, anti_patterns_sheet)

    def report_cache_without_expiry(self):
        """Generates the "Cache Without Expiry" report sheet."""

        # Worksheet 6 - [Cache Without Expiry]
        logger.info(
            '------------------- Cache Without Expiry -----------------------')   # noqa pylint: disable=C0301
        cache_without_expiry_sheet = self.workbook.add_worksheet(
            name='Cache Without Expiry')

        # Headings
        self.qualification_report_heading(
            cache_without_expiry_mapping["headers"], cache_without_expiry_sheet)   # noqa pylint: disable=C0301

        row = 1

        proxy_map = self.export_data['proxy_dependency_map']
        for proxy, values in proxy_map.items():
            if values.get("unifier_created"):
                continue

            cache_without_expiry = values.get('qualification', {}).get('CacheWithoutExpiry', {})   # noqa pylint: disable=C0301
            for policy, value in cache_without_expiry.items():
                col = 0
                cache_without_expiry_sheet.write(row, col, self.org_name)
                col += 1
                cache_without_expiry_sheet.write(row, col, proxy)
                col += 1
                cache_without_expiry_sheet.write(row, col, policy)
                col += 1
                cache_without_expiry_sheet.write(row, col, value)

                row += 1

        cache_without_expiry_sheet.autofit()
        # Info block
        self.qualification_report_info_box(
            cache_without_expiry_mapping, cache_without_expiry_sheet)

    def report_apps_without_api_products(self):
        """Generates the "Apps Without ApiProducts" report sheet."""
        # Worksheet 7 - [Apps Without ApiProducts]
        logger.info(
            '------------------- Apps Without ApiProducts -----------------------')   # noqa pylint: disable=C0301
        apps_without_products_sheet = self.workbook.add_worksheet(
            name='Apps Without ApiProducts')

        # Headings
        self.qualification_report_heading(
            apps_without_api_products_mapping["headers"], apps_without_products_sheet)   # noqa pylint: disable=C0301

        org_config = self.export_data.get('orgConfig')
        row = 1

        apps = org_config['apps']
        for app, value in apps.items():
            credentials = value.get('credentials', [])
            if len(credentials) == 0:
                col = 0
                apps_without_products_sheet.write(row, col, self.org_name)   # noqa pylint: disable=C0301
                # app name
                col += 1
                apps_without_products_sheet.write(row, col, value.get('name', 'Unknown App Name'))   # noqa pylint: disable=C0301
                # id
                col += 1
                apps_without_products_sheet.write(row, col, app)
                # status
                col += 1
                apps_without_products_sheet.write(
                    row, col, 'No Credentials Found')
            else:
                no_products = False
                for each_cred in credentials:
                    if len(each_cred.get('apiProducts', [])) == 0:
                        no_products = True
                if no_products:
                    col = 0
                    apps_without_products_sheet.write(row, col, self.org_name)   # noqa pylint: disable=C0301
                    # app name
                    col += 1
                    apps_without_products_sheet.write(row, col, value['name'])
                    # id
                    col += 1
                    apps_without_products_sheet.write(row, col, app)
                    # status
                    col += 1
                    apps_without_products_sheet.write(
                        row, col, 'No apiProducts associated')

        apps_without_products_sheet.autofit()
        # Info block
        self.qualification_report_info_box(
            apps_without_api_products_mapping, apps_without_products_sheet)  # noqa

    def report_json_path_enabled(self):
        """Generates the "Json Path Enabled" report sheet."""

        # Worksheet 8 - [Json Path Enabled]
        logger.info(
            '------------------- Json Path Enabled -----------------------')  # noqa
        json_path_enabled_sheet = self.workbook.add_worksheet(
            name='Json Path Enabled')

        # Headings
        self.qualification_report_heading(
            json_path_enabled_mapping["headers"], json_path_enabled_sheet)

        row = 1

        proxy_map = self.export_data['proxy_dependency_map']
        for proxy, values in proxy_map.items():
            if values.get("unifier_created"):
                continue

            json_path_enabled = values.get('qualification', {}).get('JsonPathEnabled', {})  # noqa

            for policy, value in json_path_enabled.items():
                col = 0
                json_path_enabled_sheet.write(row, col, self.org_name)
                col += 1
                json_path_enabled_sheet.write(row, col, proxy)
                col += 1
                json_path_enabled_sheet.write(row, col, policy)
                col += 1
                json_path_enabled_sheet.write(row, col, value)

                row += 1

        json_path_enabled_sheet.autofit()
        # Info block
        self.qualification_report_info_box(
            json_path_enabled_mapping, json_path_enabled_sheet)

    def report_cname_anomaly(self):
        """Generates the "CName Anomaly" report sheet."""

        # Worksheet 9 - [CName Anomaly]
        logger.info('------------------- CName Anomaly -----------------------')  # noqa
        cname_anamoly = self.workbook.add_worksheet(name='CName Anomaly')

        # Headings
        self.qualification_report_heading(
            cname_anomaly_mapping["headers"], cname_anamoly)

        env_config = self.export_data.get('envConfig')
        row = 1

        for key, value in env_config.items():
            vhosts = value['vhosts']
            for vhost in vhosts:
                if vhosts[vhost].get('useBuiltInFreeTrialCert', False):
                    # org name
                    col = 0
                    cname_anamoly.write(row, col, self.org_name)
                    # Env name
                    col += 1
                    cname_anamoly.write(row, col, key)
                    col += 1
                    cname_anamoly.write(row, col, vhosts[vhost]['name'])
                    row += 1

        cname_anamoly.autofit()
        # Info block
        self.qualification_report_info_box(cname_anomaly_mapping, cname_anamoly)  # noqa

    def report_unsupported_policies(self):
        """Generates the "Unsupported Policies" report sheet."""

        # Worksheet 10 - [Unsupported Policies]
        logger.info(
            '------------------- Unsupported Policies -----------------------')  # noqa
        unsupported_polices_sheet = self.workbook.add_worksheet(
            name='Unsupported Policies')

        # Headings
        self.qualification_report_heading(
            unsupported_polices_mapping["headers"], unsupported_polices_sheet)

        row = 1

        proxy_map = self.export_data['proxy_dependency_map']
        for proxy, values in proxy_map.items():
            if values.get("unifier_created"):
                continue

            policies = values.get('qualification', {}).get('policies', {})
            for policy_name, policy in policies.items():
                col = 0
                unsupported_polices_sheet.write(row, col, self.org_name)
                col += 1
                unsupported_polices_sheet.write(row, col, proxy)
                col += 1
                unsupported_polices_sheet.write(row, col, policy_name)
                col += 1
                unsupported_polices_sheet.write(row, col, policy)

                row += 1

        unsupported_polices_sheet.autofit()
        # Info block
        self.qualification_report_info_box(
            unsupported_polices_mapping, unsupported_polices_sheet)

    def report_api_limits(self):
        """Generates the "Product Limits - API Limits" report sheet."""

        # Worksheet 12 - [Product Limits - API Limits]
        logger.info(
            '------------------- Product Limits - API Limits -----------------------')  # noqa
        api_limits_sheet = self.workbook.add_worksheet(
            name='Product Limits - API Limits')

        # Headings
        self.qualification_report_heading(
            api_limits_mapping["headers"], api_limits_sheet)

        allowed_no_of_revisions_per_proxy = self.backend_cfg.get(
            'inputs', 'NO_OF_API_REVISIONS_IN_API_PROXY')
        org_config = self.export_data.get('orgConfig')
        row = 1

        for key, value in org_config['apis'].items():
            # Org name
            col = 0
            api_limits_sheet.write(row, col, self.org_name)
            # Api name
            col += 1
            api_limits_sheet.write(row, col, key)
            # Revisions
            col += 1
            if len(value) > int(allowed_no_of_revisions_per_proxy):
                api_limits_sheet.write(row, col, len(value), self.danger_format)   # noqa pylint: disable=C0301
            else:
                api_limits_sheet.write(row, col, len(value))
            row += 1

        api_limits_sheet.autofit()
        # Info block
        self.qualification_report_info_box(api_limits_mapping, api_limits_sheet)   # noqa pylint: disable=C0301

    def report_org_limits(self):
        """Generates the "Product Limits - Org Limits" report sheet."""

        # Worksheet 13 - [Product Limits - Org Limits]
        logger.info(
            '------------------- Product Limits - Org Limits -----------------------')  # noqa
        org_limits_sheet = self.workbook.add_worksheet(
            name='Product Limits - Org Limits')
        allowed_no_of_kvms_per_org = self.backend_cfg.get(
            'inputs', 'NO_OF_KVMS_PER_ORG')
        allowed_no_of_apps_per_org = self.backend_cfg.get(
            'inputs', 'NO_OF_APPS_PER_ORG')
        allowed_no_of_apirproducts_per_org = self.backend_cfg.get(
            'inputs', 'NO_OF_API_PRODUCTS_PER_ORG')

        # Headings
        self.qualification_report_heading(
            org_limits_mapping["headers"], org_limits_sheet)

        org_config = self.export_data.get('orgConfig')
        row = 1

        # Org name
        col = 0
        org_limits_sheet.write(row, col, self.org_name)
        # Developer count
        col += 1
        org_limits_sheet.write(row, col, len(org_config['developers']))
        # KVM count
        col += 1
        if len(org_config['kvms']) > int(allowed_no_of_kvms_per_org):
            org_limits_sheet.write(row, col, len(
                org_config['kvms']), self.danger_format)
        else:
            org_limits_sheet.write(row, col, len(org_config['kvms']))

        # encrypted kvm
        col += 1
        encrypted_count = 0
        for _, kvm_content in org_config['kvms'].items():
            if kvm_content.get("encrypted"):
                encrypted_count = encrypted_count+1

        if encrypted_count > 0:
            org_limits_sheet.write(row, col, encrypted_count, self.danger_format)   # noqa pylint: disable=C0301
        else:
            org_limits_sheet.write(row, col, encrypted_count)

        # non encrypted kvm
        col += 1
        org_limits_sheet.write(row, col, len(org_config['kvms']) - encrypted_count)  # noqa

        # apps count
        col += 1
        if len(org_config['apps']) > int(allowed_no_of_apps_per_org):
            org_limits_sheet.write(row, col, len(
                org_config['apps']), self.danger_format)
        else:
            org_limits_sheet.write(row, col, len(org_config['apps']))

        # api products count
        col += 1
        if len(org_config['apiProducts']) > int(allowed_no_of_apirproducts_per_org):  # noqa
            org_limits_sheet.write(row, col, len(
                org_config['apiProducts']), self.danger_format)
        else:
            org_limits_sheet.write(row, col, len(org_config['apiProducts']))

        # api count
        col += 1
        org_limits_sheet.write(row, col, len(org_config['apis']))

        org_limits_sheet.autofit()
        # Info block
        self.qualification_report_info_box(org_limits_mapping, org_limits_sheet)  # noqa

    def report_env_limits(self):
        """Generates the "Product Limits - Env Limits" report sheet."""

        # Worksheet 14 - [Product Limits - Env Limits]
        logger.info(
            '------------------- Product Limits - Env Limits -----------------------')  # noqa
        env_limits_sheet = self.workbook.add_worksheet(
            name='Product Limits - Env Limits')

        allowed_no_of_kvms_per_env = self.backend_cfg.get(
            'inputs', 'NO_OF_KVMS_PER_ENV')
        allowed_no_of_target_servers_per_env = self.backend_cfg.get(
            'inputs', 'NO_OF_TARGET_SERVERS_PER_ENV')

        # Headings
        self.qualification_report_heading(
            env_limits_mapping["headers"], env_limits_sheet)

        env_config = self.export_data.get('envConfig')
        row = 1

        for key, value in env_config.items():
            # Org name
            col = 0
            env_limits_sheet.write(row, col, self.org_name)
            # Env name
            col += 1
            env_limits_sheet.write(row, col, key)
            # Target servers
            col += 1
            if len(value['targetServers']) > int(allowed_no_of_target_servers_per_env):  # noqa
                env_limits_sheet.write(row, col, len(
                    value['targetServers']), self.danger_format)
            else:
                env_limits_sheet.write(row, col, len(value['targetServers']))
            # Caches
            col += 1
            env_limits_sheet.write(row, col, len(value['caches']))
            # Certs
            col += 1
            certs = 0
            for _, keystorecontent in value['keystores'].items():
                certs = certs + len(keystorecontent['aliases'])
            env_limits_sheet.write(row, col, certs)
            # KVMs
            col += 1
            if len(value['kvms']) > int(allowed_no_of_kvms_per_env):
                env_limits_sheet.write(row, col, len(
                    value['kvms']), self.danger_format)
            else:
                env_limits_sheet.write(row, col, len(value['kvms']))

            # encrypted kvm
            col += 1
            encrypted_count = 0
            for kvm, kvm_content in value['kvms'].items():
                if len(kvm) != 0 and kvm_content.get("encrypted"):
                    encrypted_count = encrypted_count+1

            if encrypted_count > 0:
                env_limits_sheet.write(row, col, encrypted_count, self.danger_format)  # noqa
            else:
                env_limits_sheet.write(row, col, encrypted_count)

            # non encrypted kvm
            col += 1
            env_limits_sheet.write(row, col, len(value['kvms']) - encrypted_count)  # noqa

            # Virtual hosts
            col += 1
            env_limits_sheet.write(row, col, len(value['vhosts']))
            # references
            col += 1
            env_limits_sheet.write(row, col, len(value['references']))
            row += 1

        env_limits_sheet.autofit()
        # Info block
        self.qualification_report_info_box(env_limits_mapping, env_limits_sheet)   # noqa pylint: disable=C0301

    def report_api_with_multiple_basepaths(self):
        """Generates the "APIs With Multiple BasePaths" report sheet."""

        # Worksheet 15 - [APIs With Multiple BasePaths]
        logger.info(
            '------------------- APIs With Multiple BasePaths -----------------------')  # noqa
        api_with_multiple_basepaths_sheet = self.workbook.add_worksheet(
            name='APIs With Multiple BasePaths')

        # Headings
        self.qualification_report_heading(
            api_with_multiple_basepath_mapping["headers"], api_with_multiple_basepaths_sheet)     # noqa pylint: disable=C0301

        row = 1

        proxy_map = self.export_data['proxy_dependency_map']
        for proxy, values in proxy_map.items():
            if values.get("unifier_created"):
                continue

            base_paths = values.get('qualification', {}).get('base_paths', [])  # noqa
            base_paths = [
                str(path) if path is not None else 'None' for path in base_paths]  # noqa
            col = 0
            api_with_multiple_basepaths_sheet.write(row, col, self.org_name)
            col += 1
            api_with_multiple_basepaths_sheet.write(row, col, proxy)
            col += 1
            if len(base_paths) > 5:
                api_with_multiple_basepaths_sheet.write(
                    row, col, '\n'.join(base_paths), self.danger_format)
            elif len(base_paths) > 1:
                api_with_multiple_basepaths_sheet.write(
                    row, col, '\n'.join(base_paths), self.yellow_format)
            elif len(base_paths) == 1:
                api_with_multiple_basepaths_sheet.write(
                    row, col, '\n'.join(base_paths))

            row += 1

        api_with_multiple_basepaths_sheet.autofit()
        # Info block
        self.qualification_report_info_box(
            api_with_multiple_basepath_mapping, api_with_multiple_basepaths_sheet)  # noqa

    def sharding(self):
        """Generates the "Target Environments" report sheet (Sharding info)."""

        # Worksheet 11 - [Sharded envs]
        logger.info(
            '------------------- Sharded Env Info -----------------------')  # noqa
        sharding_output_sheet = self.workbook.add_worksheet(
            name='Target Environments')

        # Headings
        self.qualification_report_heading(
            sharding_output["headers"], sharding_output_sheet)

        sharding_env_output = self.export_data.get('sharding_output')
        row = 1

        for env, sharded_envs in sharding_env_output.items():
            for sharded_env, content in sharded_envs.items():
                col = 0
                sharding_output_sheet.write(row, col, self.org_name)
                col += 1
                sharding_output_sheet.write(row, col, env)
                col += 1
                sharding_output_sheet.write(row, col, sharded_env)
                col += 1
                proxies_list = content.get("proxyname", [])
                sharding_output_sheet.write(row, col, '\n'.join(proxies_list))
                col += 1
                shared_flows_list = content.get("shared_flow", [])
                sharding_output_sheet.write(row, col, '\n'.join(shared_flows_list))   # noqa pylint: disable=C0301
                col += 1
                sharding_output_sheet.write(row, col, len(proxies_list))
                col += 1
                sharding_output_sheet.write(row, col, len(shared_flows_list))
                col += 1
                sharding_output_sheet.write(row, col, len(
                    proxies_list) + len(shared_flows_list))
                row += 1

        sharding_output_sheet.autofit()
        # Info block
        self.qualification_report_info_box(sharding_output, sharding_output_sheet)   # noqa pylint: disable=C0301

    def report_alias_keycert(self):
        """Generates the "Aliases with private keys" report sheet."""
        logger.info(
            '------------------- Aliases with private keys -----------------------')  # noqa
        aliases_with_private_keys_sheet = self.workbook.add_worksheet(
            name='Aliases with private keys')

        # Headings
        self.qualification_report_heading(
            aliases_with_private_keys["headers"], aliases_with_private_keys_sheet)   # noqa pylint: disable=C0301

        row = 1
        for env, content in self.export_data['envConfig'].items():  # noqa
            for keystore, keystore_content in content.get('keystores').items():  # noqa
                if keystore_content.get('alias_data'):
                    for alias, alias_content in keystore_content.get('alias_data').items():  # noqa
                        col = 0
                        aliases_with_private_keys_sheet.write(row, col, self.org_name)   # noqa pylint: disable=C0301
                        col += 1
                        aliases_with_private_keys_sheet.write(row, col, env)
                        col += 1
                        aliases_with_private_keys_sheet.write(row, col, keystore)   # noqa pylint: disable=C0301
                        col += 1
                        aliases_with_private_keys_sheet.write(row, col, alias)
                        col += 1
                        if alias_content.get('keyName'):
                            aliases_with_private_keys_sheet.write(
                                row, col, alias_content.get('keyName'), self.danger_format)  # noqa
                        row += 1
        aliases_with_private_keys_sheet.autofit()
        # Info block
        self.qualification_report_info_box(
            aliases_with_private_keys, aliases_with_private_keys_sheet)

    def sharded_proxies(self):
        """Generates the "Sharded Proxies" report sheet."""
        logger.info(
            '------------------- Sharded Proxies -----------------------')
        sharded_proxies_sheet = self.workbook.add_worksheet(name='Sharded Proxies')  # noqa

        # Headings
        self.qualification_report_heading(
            sharded_proxies["headers"], sharded_proxies_sheet)

        row = 1

        proxy_map = self.export_data['proxy_dependency_map']
        for proxy, values in proxy_map.items():
            if values.get("is_split"):
                sharded_proxies_list = values.get("split_output_names")
                col = 0
                sharded_proxies_sheet.write(row, col, self.org_name)
                col += 1
                sharded_proxies_sheet.write(row, col, proxy)
                col += 1
                sharded_proxies_sheet.write(row, col, '\n'.join(sharded_proxies_list))  # noqa
                row += 1

        sharded_proxies_sheet.autofit()
        # Info block
        self.qualification_report_info_box(sharded_proxies, sharded_proxies_sheet)   # noqa pylint: disable=C0301

    def validation_report(self):
        """Generates the "Validation Report" sheet."""
        logger.info('------------------- Validation Report -----------------------')  # noqa

        validation_report_sheet = self.workbook.add_worksheet(name='Validation Report')  # noqa
        self.qualification_report_heading(validation_report["headers"], validation_report_sheet)   # noqa pylint: disable=C0301

        row = 1
        for key, value in self.export_data['validation_report'].items():
            # col = 0
            if key == "report":
                continue
            # validation_report_sheet.write(row, col, key)

            for values in value:
                col = 0
                validation_report_sheet.write(row, col, key)
                col += 1
                validation_report_sheet.write(row, col, values['name'])
                col += 1
                if values['importable']:
                    validation_report_sheet.write(row, col, values['importable'], self.green_format)   # noqa pylint: disable=C0301
                    col += 1
                    validation_report_sheet.write(row, col, 'N/A')
                if not values['importable']:
                    validation_report_sheet.write(row, col, values['importable'], self.danger_format)   # noqa pylint: disable=C0301
                    col += 1
                    reason_str = {}
                    violations = values.get('reason', [{'violations': []}])
                    if len(violations[0].get('violations', [])) == 0:
                        error_code = values.get('error', {}).get('code', 0)
                        message = values.get('error', {}).get('message', '')
                        reason_str = {'violations': [
                            {'description': f"code: {error_code}. error_message: {message}"} # noqa
                        ]}
                    else:
                        reason_str = violations[0].get('violations', [])

                    validation_report_sheet.write(row, col, json.dumps(reason_str, indent=2))   # noqa pylint: disable=C0301
                col += 1
                if 'imported' in values:
                    validation_report_sheet.write(row, col, values['imported'])   # noqa pylint: disable=C0301
                else:
                    validation_report_sheet.write(row, col, 'UNKNOWN')
                row += 1
        validation_report_sheet.autofit()

    def report_org_resourcefiles(self):
        """Generates the "Org Level Resourcefiles" report sheet."""

        logger.info(
            '------------------- Org level Resourcefiles -----------------------')  # noqa
        org_resourcefiles_sheet = self.workbook.add_worksheet(
            name='Org Level Resourcefiles')

        # Headings
        self.qualification_report_heading(
            org_resourcefiles["headers"], org_resourcefiles_sheet)

        row = 1

        for key in self.export_data['orgConfig']["resourcefiles"]:  # noqa
            col = 0
            org_resourcefiles_sheet.write(row, col, self.org_name)
            col += 1
            org_resourcefiles_sheet.write(row, col, key)

            row += 1
        org_resourcefiles_sheet.autofit()
        # Info block
        self.qualification_report_info_box(
            org_resourcefiles, org_resourcefiles_sheet)

    def report_api_traffic(self):
        """Generates the "API Traffic" report sheet."""
        logger.info(
            '------------------- API Traffic -----------------------')
        api_traffic_sheet = self.workbook.add_worksheet(
            name='API Traffic')

        start_date = self.cfg.get('inputs', 'ANALYTICS_START_DATE')
        end_date = self.cfg.get('inputs', 'ANALYTICS_END_DATE')

        api_traffic_mapping["headers"][3] = f"Total Traffic {start_date} - {end_date}"

        # Headings
        self.qualification_report_heading(
            api_traffic_mapping["headers"], api_traffic_sheet)

        env_config = self.export_data.get('envConfig')
        row = 1

        for env, value in env_config.items():
            api_traffic_data = value.get('api_traffic', {})
            if not api_traffic_data:
                logger.info(f"No API traffic data found for environment: {env}")
                continue

            for proxy_data in api_traffic_data.values():
                col = 0
                api_traffic_sheet.write(row, col, self.org_name)
                col += 1
                api_traffic_sheet.write(row, col, env)
                col += 1
                api_traffic_sheet.write(row, col, proxy_data.get('proxy_name', 'N/A'))
                col += 1
                api_traffic_sheet.write(row, col, proxy_data.get('total_traffic', 0))
                row += 1

        api_traffic_sheet.autofit()

        # Info block
        self.qualification_report_info_box(
            api_traffic_mapping, api_traffic_sheet)

    def report_network_topology(self):
        """Generates the "Apigee (4G) components" report sheet (Topology)."""

        # Worksheet 16 - [Apigee OPDK/Edge (4G) components]
        logger.info(
            '------------------- Apigee OPDK/Edge (4G) components -----------------------')  # noqa
        topology_installation_sheet = self.workbook.add_worksheet(
            name='Apigee (4G) components')

        # Headings
        self.qualification_report_heading(
            topology_installation_mapping["headers"], topology_installation_sheet)  # noqa

        row = 1

        if len(self.topology_mapping) != 0:
            for dc in self.topology_mapping['data_center_mapping']:

                for pod in self.topology_mapping['data_center_mapping'][dc]:

                    for pod_instance in self.topology_mapping['data_center_mapping'][dc][pod]:   # noqa pylint: disable=C0301
                        col = 0
                        topology_installation_sheet.write(row, col, dc)
                        col += 1
                        topology_installation_sheet.write(row, col, pod)
                        col += 1

                        topology_installation_sheet.write(
                            row, col, '\n'.join(pod_instance['type']))
                        col += 1

                        for col_key_map in topology_installation_mapping["key_mapping"]:   # noqa pylint: disable=C0301
                            topology_installation_sheet.write(
                                row, col, pod_instance[col_key_map])
                            col += 1

                        row += 1
        topology_installation_sheet.autofit()

    def qualification_report_summary(self):
        """Generates the "Qualification Summary" sheet."""

        # Worksheet 15 - [Qualification Summary]
        logger.info(
            '------------------- Qualification Summary -----------------------')  # noqa
        qualification_summary_sheet = self.workbook.add_worksheet(
            name='Qualification Summary')

        col = 0
        qualification_summary_sheet.set_column(
            col, col+1, int(report_summary["col_width"])+1)
        qualification_summary_sheet.merge_range(
            f'A{report_summary["header_row"]}:B{report_summary["header_row"]}', report_summary["header_text"], self.summary_main_header_format)   # noqa pylint: disable=C0301

        row = report_summary["header_row"]+1

        for block in report_summary["blocks"]:

            if "APIGEE_SOURCE" in block and self.cfg.get('inputs', 'SOURCE_APIGEE_VERSION') != block["APIGEE_SOURCE"]:   # noqa pylint: disable=C0301
                break

            qualification_summary_sheet.merge_range(
                f'A{row}:B{row}', block["header"], self.summary_block_header_format)   # noqa pylint: disable=C0301
            row = row+1

            col = 0
            for row_sheet in block["sheets"]:
                if "link_of_text" in row_sheet:
                    qualification_summary_sheet.write_url(
                        f'A{row}', row_sheet["link_of_text"], self.summary_link_format, string=row_sheet["text_col"])   # noqa pylint: disable=C0301
                else:
                    qualification_summary_sheet.write(
                        row-1, col, row_sheet["text_col"], self.summary_format)

                qualification_summary_sheet.write_formula(
                    f'B{row}', row_sheet["result_col"], cell_format=self.summary_format)  # noqa

                qualification_summary_sheet.conditional_format(f'B{row}:B{row}', {  # noqa
                    'type': 'text',
                    'criteria': 'containing',
                    'value': 'PASSED',
                    'format': self.summary_cell_green_format
                })
                qualification_summary_sheet.conditional_format(f'B{row}:B{row}', {  # noqa
                    'type': 'text',
                    'criteria': 'containing',
                    'value': 'FAILED',
                    'format': self.summary_cell_danger_format
                })
                row = row+1

        self.summary_note_blue_format.set_text_wrap()
        self.summary_note_green_format.set_text_wrap()

        row = row+report_summary["note_list"]["skip_rows"]
        col = 0
        for note in report_summary["note_list"]["notes"]:
            if note["bg_color"] == "blue":
                qualification_summary_sheet.merge_range(
                    f'A{row}:B{row}', note["text"], self.summary_note_blue_format)  # noqa
            else:
                qualification_summary_sheet.merge_range(
                    f'A{row}:B{row}', note["text"], self.summary_note_green_format)  # noqa
            row = row+1

    def reverse_sheets(self):
        """Reverses the order of worksheets in the workbook."""
        self.workbook.worksheets().reverse()

    def close(self):
        """Closes the Excel workbook."""
        # Close the workbook
        self.workbook.close()
