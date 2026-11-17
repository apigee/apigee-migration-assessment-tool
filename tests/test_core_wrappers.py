
"""
Tests for the core_wrappers module.
"""
import unittest
from unittest.mock import patch
from configparser import ConfigParser

from core_wrappers import (
    pre_validation_checks,
    export_artifacts,
    validate_artifacts,
    visualize_artifacts,
    qualification_report,
    get_topology,
)


class TestCoreWrappers(unittest.TestCase):
    """
    Test cases for the core_wrappers module.
    """

    def setUp(self):
        """
        Set up the test case.
        """
        self.cfg = ConfigParser()
        self.cfg.add_section('inputs')
        self.cfg.set('inputs', 'SOURCE_URL', 'http://source.com')
        self.cfg.set('inputs', 'SOURCE_ORG', 'source_org')
        self.cfg.set('inputs', 'SOURCE_AUTH_TYPE', 'basic')
        self.cfg.set('inputs', 'SOURCE_APIGEE_VERSION', 'OPDK')
        self.cfg.set('inputs', 'TARGET_DIR', '/tmp')
        self.cfg.set('inputs', 'SSL_VERIFICATION', 'False')
        self.cfg.set('inputs', 'TARGET_URL', 'http://target.com')
        self.cfg.set('inputs', 'GCP_PROJECT_ID', 'gcp_project')
        self.cfg.set('inputs', 'TARGET_COMPARE', 'False')

    @patch('core_wrappers.get_source_auth_token')
    @patch('core_wrappers.ApigeeClassic')
    @patch('core_wrappers.get_access_token')
    @patch('core_wrappers.ApigeeNewGen')
    def test_pre_validation_checks_success(self, mock_newgen,
                                           mock_get_access_token,
                                           mock_classic,
                                           mock_get_source_auth_token):
        """
        Test the pre_validation_checks function for success.
        """
        mock_get_source_auth_token.return_value = 'source_token'
        mock_classic.return_value.get_org.return_value = {'name': 'source_org'}
        mock_get_access_token.return_value = 'gcp_token'
        mock_newgen.return_value.validate_permissions.return_value = []
        mock_newgen.return_value.get_org.return_value = {
            'name': 'gcp_project'}
        self.assertTrue(pre_validation_checks(self.cfg))

    @patch('core_wrappers.parse_config')
    @patch('core_wrappers.get_source_auth_token')
    @patch('core_wrappers.create_dir')
    @patch('core_wrappers.ApigeeExporter')
    @patch('core_wrappers.sharding')
    # noqa pylint: disable=too-many-arguments, unused-argument, too-many-positional-arguments 
    def test_export_artifacts(self, mock_sharding, mock_exporter,
                              mock_create_dir,
                              mock_get_source_auth_token,
                              mock_parse_config):
        """
        Test the export_artifacts function.
        """
        mock_parse_config.return_value.get.return_value = 'export'
        mock_get_source_auth_token.return_value = 'source_token'
        mock_exporter.return_value.get_export_data.return_value = {
            'orgConfig': {}, 'envConfig': {}}
        mock_sharding.proxy_dependency_map.return_value = {}
        result = export_artifacts(self.cfg, ['all'])
        self.assertIn('proxy_dependency_map', result)

    @patch('core_wrappers.parse_config')
    @patch('core_wrappers.create_dir')
    @patch('core_wrappers.get_access_token')
    @patch('core_wrappers.parse_json')
    @patch('core_wrappers.ApigeeValidator')
    # noqa pylint: disable=too-many-arguments, unused-argument, too-many-positional-arguments
    def test_validate_artifacts(self, mock_validator, mock_parse_json,
                                mock_get_access_token, mock_create_dir,
                                mock_parse_config):
        """
        Test the validate_artifacts function.
        """
        mock_parse_config.return_value.get.return_value = 'export'
        mock_get_access_token.return_value = 'gcp_token'
        mock_parse_json.return_value = {}
        (mock_validator.return_value.
         validate_env_targetservers.return_value) = []
        export_data = {
            'envConfig': {'test': {'targetServers': {},
                                   'resourcefiles': {},
                                   'flowhooks': {},
                                   'kvms': {}}},
            'orgConfig': {'kvms': {}, 'developers': {},
                          'apiProducts': {}, 'apps': {}}
        }
        result = validate_artifacts(self.cfg, ['all'], export_data)
        self.assertIsInstance(result, dict)

    @patch('core_wrappers.parse_config')
    @patch('core_wrappers.nx.DiGraph')
    @patch('core_wrappers.Network')
    # pylint: disable=unused-argument
    def test_visualize_artifacts(self, mock_network, mock_digraph,
                                 mock_parse_config):
        """
        Test the visualize_artifacts function.
        """
        mock_parse_config.return_value.get.return_value = 'visualization.html'
        export_data = {'orgConfig': {}, 'envConfig': {}}
        report = {'report': {}}
        visualize_artifacts(self.cfg, export_data, report)
        mock_network.return_value.show.assert_called_with(
            '/tmp/visualization.html')

    @patch('core_wrappers.parse_config')
    @patch('core_wrappers.Network')
    def test_visualize_artifacts_escapes_html(
        self, mock_network, mock_parse_config
    ):
        """Test visualize_artifacts HTML-escapes untrusted graph tooltips."""
        mock_parse_config.return_value.get.return_value = 'visualization.html'
        self.cfg.set(
            'inputs', 'SOURCE_ORG', 'org"><img src=x onerror=alert(1)>'
        )
        export_data = {
            'orgConfig': {
                'apis': {'<script>alert(1)</script>': {}}
            },
            'envConfig': {
                'dev" onclick="alert(2)': {
                    'targetServers': {'ts<svg/onload=alert(3)>': {}}
                }
            },
        }
        report = {
            'report': {},
            'apis': [
                {
                    'name': '<script>alert(1)</script>',
                    'importable': False,
                    'reason': [
                        {'violations': [{'description': '<img/src=x>'}]}
                    ],
                }
            ],
            'dev" onclick="alert(2) | targetServers': [
                {
                    'name': 'ts<svg/onload=alert(3)>',
                    'importable': False,
                    'error': {'code': 400, 'message': '<script>xss</script>'},
                    'error_msg': {'message': '<script>xss</script>'},
                }
            ],
        }
        visualize_artifacts(self.cfg, export_data, report)
        graph = mock_network.return_value.from_nx.call_args[0][0]
        for _, attrs in graph.nodes(data=True):
            title = attrs.get('title', '')
            self.assertNotIn('<script>', title)
            self.assertNotIn('<img', title)
            self.assertNotIn('<svg', title)
            self.assertNotIn('" onclick="', title)

    @patch('core_wrappers.QualificationReport')
    def test_qualification_report(self, mock_qualification_report):
        """
        Test the qualification_report function.
        """
        backend_cfg = ConfigParser()
        backend_cfg.add_section('report')
        backend_cfg.set('report', 'QUALIFICATION_REPORT', 'report.xlsx')
        export_data = {}
        topology_mapping = {}
        qualification_report(
                                self.cfg, backend_cfg,
                                export_data, topology_mapping
                                )
        mock_qualification_report.return_value.close.assert_called_once()

    @patch('core_wrappers.get_source_auth_token')
    @patch('core_wrappers.ApigeeTopology')
    def test_get_topology(self, mock_topology, mock_get_source_auth_token):
        """
        Test the get_topology function.
        """
        mock_get_source_auth_token.return_value = 'source_token'
        mock_topology.return_value.get_topology_mapping.return_value = {}
        mock_topology.return_value.get_data_center_mapping.return_value = {}
        result = get_topology(self.cfg)
        self.assertIn('pod_component_mapping', result)


if __name__ == '__main__':
    unittest.main()
