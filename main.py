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

from core_wrappers import *
from utils import (
    write_json,
    parse_json,
    get_env_variable
)
from base_logger import logger
import argparse


def main():
    # Parse Input
    cfg = parse_config('input.properties')
    backend_cfg = parse_config('backend.properties')
    parser = argparse.ArgumentParser(description='details',
                                     usage='use "%(prog)s --help" for more information', formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--resources',
                        type=str,
                        dest='resources',
                        # help='Resources to be exported',
                        help="""resources can be one of or comma seperated list of \n
        * targetservers
        * keyvaluemaps
        * references
        * resourcefiles
        * keystores
        * flowhooks
        * developers
        * apiproducts
        * apis
        * apps
                        
        For Apigee Environment level objects choose
            -> targetservers,keyvaluemaps,references,resourcefiles,keystores,flowhooks

        For Apigee Organization level objects choose
            -> org_keyvaluemaps,developers,apiproducts,apis,apps,sharedflows

        Example1: --resources targetservers,keyvaluemaps
        Example2: --resources keystores,apps
                        """)

    args = parser.parse_args()
    resources_list = args.resources.split(',') if args.resources else []

    # Pre validation checks
    if(not pre_validation_checks(cfg)):
        logger.error("Pre validation checks failed. Please, check...")
        return

    topology_mapping = {}
    export_data_file = f"{cfg.get('inputs', 'TARGET_DIR')}/{cfg.get('export','EXPORT_DIR')}/{cfg.get('export', 'EXPORT_FILE')}"
    export_data = parse_json(export_data_file)

    report_data_file = f"{cfg.get('inputs', 'TARGET_DIR')}/{cfg.get('export','EXPORT_DIR')}/report.json"
    report = parse_json(report_data_file)

    if not export_data.get('export', False):
        export_data['export'] = False
        topology_mapping = {}

        # Export Artifacts from Apigee OPDK/Edge (4G)
        if resources_list == []:
            logger.error(
                f'Please specify --resources argument. To get the complete list of supported resources use -h with the script')
            return

        export_data = export_artifacts(cfg, resources_list)
        export_data['export'] = True
        write_json(export_data_file, export_data)

    if not report.get('report', False) or not export_data.get('validation_report', False):
        report = validate_artifacts(cfg, export_data)
        report['report'] = True
        export_data['validation_report'] = report
        write_json(export_data_file, export_data)
        write_json(report_data_file, report)
    # Visualize artifacts
    if not (os.environ.get("IGNORE_VIZ") == "true"):
        visualize_artifacts(cfg, export_data, report)

    # get Apigee OPDK/Edge (4G) topology mapping
    if not (os.environ.get("IGNORE_OPDK_TOPOLOGY") == "true"):
        SOURCE_APIGEE_VERSION = cfg.get('inputs', 'SOURCE_APIGEE_VERSION')
        if (SOURCE_APIGEE_VERSION == 'OPDK'):
            topology_mapping = get_topology(cfg)

    # Qualification report
    qualification_report(cfg, backend_cfg, export_data, topology_mapping)


if __name__ == '__main__':
    main()
