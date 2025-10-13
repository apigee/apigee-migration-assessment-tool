"""
Tests for the qualification_report module.
"""
import unittest
from unittest.mock import Mock, patch

from qualification_report import QualificationReport


# pylint: disable=too-many-instance-attributes,too-many-public-methods
class TestQualificationReport(unittest.TestCase):
    """
    Test cases for the QualificationReport class.
    """

    def setUp(self):
        """
        Set up the test case.
        """
        self.mock_workbook = Mock()
        self.patcher = patch('qualification_report.xlsxwriter.Workbook',
                             return_value=self.mock_workbook)
        self.mock_workbook_class = self.patcher.start()

        def create_mapping(headers):
            return {
                "headers": headers,
                "info_block": {
                    "text": "test",
                    "col_merge": 1,
                    "text_line_no_for_col_count": 0,
                    "start_row": 1,
                    "end_row": 10
                }
            }

        self.proxies_per_env_mapping = create_mapping(
            ["Org", "Env", "Proxies", "SharedFlows", "Total"])
        self.northbound_mtls_mapping = create_mapping(
            ["Org", "Env", "VHost", "SSL Enabled", "Client Auth Enabled",
             "Keystore"])
        self.company_and_developers_mapping = create_mapping(
            ["Org", "Company"])
        self.anti_patterns_mapping = create_mapping(
            ["Org", "Proxy", "Policy", "Distributed", "Synchronous"])
        self.cache_without_expiry_mapping = create_mapping(
            ["Org", "Proxy", "Policy", "Value"])
        self.apps_without_api_products_mapping = create_mapping(
            ["Org", "App Name", "App ID", "Status"])
        self.json_path_enabled_mapping = create_mapping(
            ["Org", "Proxy", "Policy", "Value"])
        self.cname_anomaly_mapping = create_mapping(["Org", "Env", "VHost"])
        self.unsupported_polices_mapping = create_mapping(
            ["Org", "Proxy", "Policy", "Type"])
        self.api_limits_mapping = create_mapping(["Org", "API", "Revisions"])
        self.org_limits_mapping = create_mapping(
            ["Org", "Developers", "KVMs", "Encrypted KVMs",
             "Non-Encrypted KVMs", "Apps", "API Products", "APIs"])
        self.env_limits_mapping = create_mapping(
            ["Org", "Env", "Target Servers", "Caches", "Certs", "KVMs",
             "Encrypted KVMs", "Non-Encrypted KVMs", "Virtual Hosts",
             "References"])
        self.api_with_multiple_basepath_mapping = create_mapping(
            ["Org", "Proxy", "Basepaths"])
        self.sharding_output = create_mapping(
            ["Org", "Env", "Sharded Env", "Proxies", "SharedFlows",
             "Proxy Count", "SharedFlow Count", "Total"])
        self.aliases_with_private_keys = create_mapping(
            ["Org", "Env", "Keystore", "Alias", "Key Name"])
        self.sharded_proxies = create_mapping(
            ["Org", "Proxy", "Sharded Proxies"])
        self.validation_report = create_mapping(
            ["Type", "Name", "Importable", "Reason", "Imported"])
        self.org_resourcefiles = create_mapping(["Org", "Resource File"])
        self.topology_installation_mapping = {
            "headers": ["Datacenter", "Pod", "Type", "IP Address", "Hostname",
                        "Version"],
            "key_mapping": ["internal_ip", "hostname", "version"]}
        self.report_summary = {
            "col_width": 20,
            "header_row": 1,
            "header_text": "Test Summary",
            "blocks": [],
            "note_list": {
                "skip_rows": 1,
                "notes": []
            }
        }
        self.export_data = {
            'envConfig': {},
            'orgConfig': {
                'resourcefiles': ['file1', 'file2']
            },
            'proxy_dependency_map': {},
            'sharding_output': {},
            'validation_report': {}
        }
        self.topology_mapping = {
            'data_center_mapping': {}
        }
        self.cfg = Mock()
        self.backend_cfg = Mock()
        self.org_name = 'test_org'

    def tearDown(self):
        """
        Tear down the test case.
        """
        self.patcher.stop()

    def test_init(self):
        """
        Test the __init__ method.
        """
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        self.mock_workbook_class.assert_called_once_with('test.xlsx')
        self.assertEqual(report.workbook, self.mock_workbook)
        self.assertEqual(report.export_data, self.export_data)
        self.assertEqual(report.topology_mapping, self.topology_mapping)
        self.assertEqual(report.org_name, self.org_name)
        self.assertEqual(report.cfg, self.cfg)
        self.assertEqual(report.backend_cfg, self.backend_cfg)

    @patch('qualification_report.proxies_per_env_mapping')
    def test_report_proxies_per_env(self, mock_mapping):
        """
        Test the report_proxies_per_env method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.proxies_per_env_mapping.__getitem__)
        self.export_data['envConfig'] = {
            'test_env': {
                'apis': ['api1', 'api2'],
                'sharedflows': ['sf1']
            }
        }
        self.backend_cfg.get.side_effect = ['1', '1', '2']
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_proxies_per_env()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Proxies Per Env')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 'test_env')
        mock_sheet.write.assert_any_call(1, 2, 2, report.danger_format)
        mock_sheet.write.assert_any_call(1, 3, 1)
        mock_sheet.write.assert_any_call(1, 4, 3, report.danger_format)

    @patch('qualification_report.northbound_mtls_mapping')
    def test_report_north_bound_mtls(self, mock_mapping):
        """
        Test the report_north_bound_mtls method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.northbound_mtls_mapping.__getitem__)
        self.export_data['envConfig'] = {
            'test_env': {
                'vhosts': {
                    'test_vhost': {
                        'sSLInfo': {
                            'enabled': True,
                            'clientAuthEnabled': True,
                            'keyStore': 'test_keystore'
                        }
                    }
                }
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_north_bound_mtls()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Northbound mTLS')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 'test_env')
        mock_sheet.write.assert_any_call(1, 2, 'test_vhost')
        mock_sheet.write.assert_any_call(1, 3, True, report.danger_format)
        mock_sheet.write.assert_any_call(1, 4, True, report.danger_format)
        mock_sheet.write.assert_any_call(1, 5, 'test_keystore',
                                         report.danger_format)

    @patch('qualification_report.company_and_developers_mapping')
    def test_report_company_and_developer(self, mock_mapping):
        """
        Test the report_company_and_developer method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.company_and_developers_mapping.__getitem__)
        self.export_data['orgConfig'] = {
            'companies': ['company1', 'company2']
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_company_and_developer()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Company And Developers')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 'company1')
        mock_sheet.write.assert_any_call(2, 0, 'test_org')
        mock_sheet.write.assert_any_call(2, 1, 'company2')

    @patch('qualification_report.anti_patterns_mapping')
    def test_report_anti_patterns(self, mock_mapping):
        """
        Test the report_anti_patterns method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.anti_patterns_mapping.__getitem__)
        self.export_data['proxy_dependency_map'] = {
            'proxy1': {
                'qualification': {
                    'AntiPatternQuota': {
                        'policy1': {
                            'distributed': 'true',
                            'Synchronous': 'false'
                        }
                    }
                }
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_anti_patterns()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Anti Patterns')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 'proxy1')
        mock_sheet.write.assert_any_call(1, 2, 'policy1')
        mock_sheet.write.assert_any_call(1, 3, 'true')
        mock_sheet.write.assert_any_call(1, 4, 'false')

    @patch('qualification_report.cache_without_expiry_mapping')
    def test_report_cache_without_expiry(self, mock_mapping):
        """
        Test the report_cache_without_expiry method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.cache_without_expiry_mapping.__getitem__)
        self.export_data['proxy_dependency_map'] = {
            'proxy1': {
                'qualification': {
                    'CacheWithoutExpiry': {
                        'policy1': 'value1'
                    }
                }
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_cache_without_expiry()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Cache Without Expiry')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 'proxy1')
        mock_sheet.write.assert_any_call(1, 2, 'policy1')
        mock_sheet.write.assert_any_call(1, 3, 'value1')

    @patch('qualification_report.apps_without_api_products_mapping')
    def test_report_apps_without_api_products(self, mock_mapping):
        """
        Test the report_apps_without_api_products method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.apps_without_api_products_mapping.__getitem__)
        self.export_data['orgConfig'] = {
            'apps': {
                'app1': {
                    'name': 'App 1',
                    'credentials': [{}]
                },
                'app2': {
                    'name': 'App 2',
                    'credentials': [{'apiProducts': []}]
                }
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_apps_without_api_products()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Apps Without ApiProducts')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 'App 2')
        mock_sheet.write.assert_any_call(1, 2, 'app2')
        mock_sheet.write.assert_any_call(1, 3, 'No apiProducts associated')

    @patch('qualification_report.json_path_enabled_mapping')
    def test_report_json_path_enabled(self, mock_mapping):
        """
        Test the report_json_path_enabled method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.json_path_enabled_mapping.__getitem__)
        self.export_data['proxy_dependency_map'] = {
            'proxy1': {
                'qualification': {
                    'JsonPathEnabled': {
                        'policy1': 'value1'
                    }
                }
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_json_path_enabled()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Json Path Enabled')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 'proxy1')
        mock_sheet.write.assert_any_call(1, 2, 'policy1')
        mock_sheet.write.assert_any_call(1, 3, 'value1')

    @patch('qualification_report.cname_anomaly_mapping')
    def test_report_cname_anomaly(self, mock_mapping):
        """
        Test the report_cname_anomaly method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.cname_anomaly_mapping.__getitem__)
        self.export_data['envConfig'] = {
            'env1': {
                'vhosts': {
                    'vhost1': {
                        'name': 'vhost1_name',
                        'useBuiltInFreeTrialCert': True
                    }
                }
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_cname_anomaly()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='CName Anomaly')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 'env1')
        mock_sheet.write.assert_any_call(1, 2, 'vhost1_name')

    @patch('qualification_report.unsupported_polices_mapping')
    def test_report_unsupported_policies(self, mock_mapping):
        """
        Test the report_unsupported_policies method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.unsupported_polices_mapping.__getitem__)
        self.export_data['proxy_dependency_map'] = {
            'proxy1': {
                'qualification': {
                    'policies': {
                        'policy1': 'type1'
                    }
                }
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_unsupported_policies()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Unsupported Policies')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 'proxy1')
        mock_sheet.write.assert_any_call(1, 2, 'policy1')
        mock_sheet.write.assert_any_call(1, 3, 'type1')

    @patch('qualification_report.api_limits_mapping')
    def test_report_api_limits(self, mock_mapping):
        """
        Test the report_api_limits method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.api_limits_mapping.__getitem__)
        self.export_data['orgConfig'] = {
            'apis': {
                'api1': ['rev1', 'rev2']
            }
        }
        self.backend_cfg.get.return_value = '1'
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_api_limits()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Product Limits - API Limits')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 'api1')
        mock_sheet.write.assert_any_call(1, 2, 2, report.danger_format)

    @patch('qualification_report.org_limits_mapping')
    def test_report_org_limits(self, mock_mapping):
        """
        Test the report_org_limits method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.org_limits_mapping.__getitem__)
        self.export_data['orgConfig'] = {
            'developers': ['dev1'],
            'kvms': {'kvm1': {'encrypted': True}},
            'apps': ['app1'],
            'apiProducts': ['prod1'],
            'apis': ['api1']
        }
        self.backend_cfg.get.side_effect = ['0', '0', '0']
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_org_limits()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Product Limits - Org Limits')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 1)
        mock_sheet.write.assert_any_call(1, 2, 1, report.danger_format)
        mock_sheet.write.assert_any_call(1, 3, 1, report.danger_format)
        mock_sheet.write.assert_any_call(1, 4, 0)
        mock_sheet.write.assert_any_call(1, 5, 1, report.danger_format)
        mock_sheet.write.assert_any_call(1, 6, 1, report.danger_format)
        mock_sheet.write.assert_any_call(1, 7, 1)

    @patch('qualification_report.env_limits_mapping')
    def test_report_env_limits(self, mock_mapping):
        """
        Test the report_env_limits method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.env_limits_mapping.__getitem__)
        self.export_data['envConfig'] = {
            'env1': {
                'targetServers': ['ts1'],
                'caches': ['cache1'],
                'keystores': {'ks1': {'aliases': ['alias1']}},
                'kvms': {'kvm1': {'encrypted': True}},
                'vhosts': ['vh1'],
                'references': ['ref1']
            }
        }
        self.backend_cfg.get.side_effect = ['0', '0']
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_env_limits()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Product Limits - Env Limits')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 'env1')
        mock_sheet.write.assert_any_call(1, 2, 1, report.danger_format)
        mock_sheet.write.assert_any_call(1, 3, 1)
        mock_sheet.write.assert_any_call(1, 4, 1)
        mock_sheet.write.assert_any_call(1, 5, 1, report.danger_format)
        mock_sheet.write.assert_any_call(1, 6, 1, report.danger_format)
        mock_sheet.write.assert_any_call(1, 7, 0)
        mock_sheet.write.assert_any_call(1, 8, 1)
        mock_sheet.write.assert_any_call(1, 9, 1)

    @patch('qualification_report.api_with_multiple_basepath_mapping')
    def test_report_api_with_multiple_basepaths(self, mock_mapping):
        """
        Test the report_api_with_multiple_basepaths method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.api_with_multiple_basepath_mapping.__getitem__)
        self.export_data['proxy_dependency_map'] = {
            'proxy1': {
                'qualification': {
                    'base_paths': ['/p1', '/p2']
                }
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_api_with_multiple_basepaths()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='APIs With Multiple BasePaths')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 'proxy1')
        mock_sheet.write.assert_any_call(1, 2, '/p1\n/p2',
                                         report.yellow_format)

    @patch('qualification_report.sharding_output')
    def test_sharding(self, mock_mapping):
        """
        Test the sharding method.
        """
        mock_mapping.__getitem__.side_effect = self.sharding_output.__getitem__
        self.export_data['sharding_output'] = {
            'env1': {
                'sharded_env1': {
                    'proxyname': ['p1'],
                    'shared_flow': ['sf1']
                }
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.sharding()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Target Environments')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 'env1')
        mock_sheet.write.assert_any_call(1, 2, 'sharded_env1')
        mock_sheet.write.assert_any_call(1, 3, 'p1')
        mock_sheet.write.assert_any_call(1, 4, 'sf1')
        mock_sheet.write.assert_any_call(1, 5, 1)
        mock_sheet.write.assert_any_call(1, 6, 1)
        mock_sheet.write.assert_any_call(1, 7, 2)

    @patch('qualification_report.aliases_with_private_keys')
    def test_report_alias_keycert(self, mock_mapping):
        """
        Test the report_alias_keycert method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.aliases_with_private_keys.__getitem__)
        self.export_data['envConfig'] = {
            'env1': {
                'keystores': {
                    'ks1': {
                        'alias_data': {
                            'alias1': {
                                'keyName': 'key1'
                            }
                        }
                    }
                }
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_alias_keycert()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Aliases with private keys')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 'env1')
        mock_sheet.write.assert_any_call(1, 2, 'ks1')
        mock_sheet.write.assert_any_call(1, 3, 'alias1')
        mock_sheet.write.assert_any_call(1, 4, 'key1', report.danger_format)

    @patch('qualification_report.sharded_proxies')
    def test_sharded_proxies(self, mock_mapping):
        """
        Test the sharded_proxies method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.sharded_proxies.__getitem__)
        self.export_data['proxy_dependency_map'] = {
            'proxy1': {
                'is_split': True,
                'split_output_names': ['p1', 'p2']
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.sharded_proxies()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Sharded Proxies')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 'proxy1')
        mock_sheet.write.assert_any_call(1, 2, 'p1\np2')

    @patch('qualification_report.validation_report')
    def test_validation_report(self, mock_mapping):
        """
        Test the validation_report method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.validation_report.__getitem__)
        self.export_data['validation_report'] = {
            'type1': [
                {
                    'name': 'name1',
                    'importable': True,
                    'reason': [{'violations': ['v1']}],
                    'imported': True
                },
                {
                    'name': 'name2',
                    'importable': False,
                    'reason': [{'violations': ['v2']}],
                    'imported': False
                }
            ]
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.validation_report()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Validation Report')
        mock_sheet.write.assert_any_call(1, 0, 'type1')
        mock_sheet.write.assert_any_call(1, 1, 'name1')
        mock_sheet.write.assert_any_call(1, 2, True, report.yellow_format)
        mock_sheet.write.assert_any_call(1, 4, True)
        mock_sheet.write.assert_any_call(2, 0, 'type1')
        mock_sheet.write.assert_any_call(2, 1, 'name2')
        mock_sheet.write.assert_any_call(2, 2, False, report.danger_format)
        mock_sheet.write.assert_any_call(2, 4, False)

    @patch('qualification_report.org_resourcefiles')
    def test_report_org_resourcefiles(self, mock_mapping):
        """
        Test the report_org_resourcefiles method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.org_resourcefiles.__getitem__)
        self.export_data['orgConfig'] = {
            'resourcefiles': ['rf1']
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_org_resourcefiles()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Org Level Resourcefiles')
        mock_sheet.write.assert_any_call(1, 0, 'test_org')
        mock_sheet.write.assert_any_call(1, 1, 'rf1')

    @patch('qualification_report.topology_installation_mapping')
    def test_report_network_topology(self, mock_mapping):
        """
        Test the report_network_topology method.
        """
        mock_mapping.__getitem__.side_effect = (
            self.topology_installation_mapping.__getitem__)
        self.topology_mapping['data_center_mapping'] = {
            'dc1': {
                'pod1': [
                    {
                        'type': ['type1'],
                        'internal_ip': '127.0.0.1',
                        'hostname': 'localhost',
                        'version': '1.0'
                    }
                ]
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_network_topology()
        self.mock_workbook.add_worksheet.assert_called_once_with(
            name='Apigee (4G) components')
        mock_sheet.write.assert_any_call(1, 0, 'dc1')
        mock_sheet.write.assert_any_call(1, 1, 'pod1')
        mock_sheet.write.assert_any_call(1, 2, 'type1')
        mock_sheet.write.assert_any_call(1, 3, '127.0.0.1')
        mock_sheet.write.assert_any_call(1, 4, 'localhost')
        mock_sheet.write.assert_any_call(1, 5, '1.0')

    @patch('qualification_report.report_summary')
    def test_qualification_report_summary(self, mock_summary):
        """
        Test the qualification_report_summary method.
        """
        mock_summary.__getitem__.side_effect = self.report_summary.__getitem__
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.qualification_report_summary()
        self.mock_workbook.add_worksheet.assert_called_with(
            name='Qualification Summary')

    @patch('qualification_report.report_summary')
    def test_qualification_report_summary_with_data(self, mock_summary):
        """
        Test the qualification_report_summary method with data.
        """
        self.report_summary['blocks'] = [
            {
                "header": "Block 1",
                "sheets": [
                    {
                        "text_col": "Sheet 1",
                        "result_col": "'Sheet 1'!A1"
                    }
                ]
            }
        ]
        mock_summary.__getitem__.side_effect = self.report_summary.__getitem__
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.qualification_report_summary()
        self.mock_workbook.add_worksheet.assert_called_with(
            name='Qualification Summary')
        mock_sheet.merge_range.assert_any_call(
            'A1:B1', 'Test Summary', report.summary_main_header_format)
        mock_sheet.merge_range.assert_any_call(
            'A2:B2', 'Block 1', report.summary_block_header_format)
        mock_sheet.write.assert_any_call(2, 0, 'Sheet 1',
                                         report.summary_format)
        mock_sheet.write_formula.assert_any_call(
            'B3', "'Sheet 1'!A1", cell_format=report.summary_format)

    def test_reverse_sheets(self):
        """
        Test the reverse_sheets method.
        """
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_worksheets = Mock()
        self.mock_workbook.worksheets.return_value = mock_worksheets
        report.reverse_sheets()
        mock_worksheets.reverse.assert_called_once()

    def test_close(self):
        """
        Test the close method.
        """
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        report.close()
        self.mock_workbook.close.assert_called_once()

    @patch('qualification_report.anti_patterns_mapping')
    def test_report_anti_patterns_missing_attrs(self, mock_mapping):
        """
        Test report_anti_patterns with missing XML attributes (None values).
        """
        mock_mapping.__getitem__.side_effect = (
            self.anti_patterns_mapping.__getitem__)
        self.export_data['proxy_dependency_map'] = {
            'proxy1': {
                'qualification': {
                    'AntiPatternQuota': {
                        'policy1': {
                            'distributed': None,  # Missing XML attribute
                            'Synchronous': None   # Missing XML attribute
                        }
                    }
                }
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_anti_patterns()

        # Verify complex lines work with None values
        mock_sheet.write.assert_any_call(1, 3, "None")
        mock_sheet.write.assert_any_call(1, 4, "None")

    @patch('qualification_report.anti_patterns_mapping')
    def test_report_anti_patterns_corrupted_data(self, mock_mapping):
        """
        Test report_anti_patterns with corrupted data (dict values).
        """
        mock_mapping.__getitem__.side_effect = (
            self.anti_patterns_mapping.__getitem__)
        self.export_data['proxy_dependency_map'] = {
            'proxy1': {
                'qualification': {
                    'AntiPatternQuota': {
                        'policy1': {
                            'distributed': {
                                'nested_key': 'nested_value',
                                'another_key': 123
                            },
                            'Synchronous': 'true'  # Normal string value
                        }
                    }
                }
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_anti_patterns()

        # Verify complex lines handle corrupted data
        expected_distributed = str({
            'nested_key': 'nested_value',
            'another_key': 123
        })
        mock_sheet.write.assert_any_call(1, 3, expected_distributed)
        mock_sheet.write.assert_any_call(1, 4, 'true')

    @patch('qualification_report.anti_patterns_mapping')
    def test_report_anti_patterns_with_boolean_values(self, mock_mapping):
        """
        Test report_anti_patterns method with boolean values
        (XML parser conversion).
        """
        mock_mapping.__getitem__.side_effect = (
            self.anti_patterns_mapping.__getitem__)
        self.export_data['proxy_dependency_map'] = {
            'proxy1': {
                'qualification': {
                    'AntiPatternQuota': {
                        'policy1': {
                            'distributed': True,  # XML "true" to boolean
                            'Synchronous': False  # XML "false" to boolean
                        }
                    }
                }
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_anti_patterns()

        # Verify the complex lines with multiple invocations work with booleans
        mock_sheet.write.assert_any_call(1, 3, True)   # _safe_value(True)
        mock_sheet.write.assert_any_call(1, 4, False)  # _safe_value(False)

    @patch('qualification_report.anti_patterns_mapping')
    def test_report_anti_patterns_with_integer_values(self, mock_mapping):
        """
        Test report_anti_patterns method with integer values
        (XML parser conversion).
        """
        mock_mapping.__getitem__.side_effect = (
            self.anti_patterns_mapping.__getitem__)
        self.export_data['proxy_dependency_map'] = {
            'proxy1': {
                'qualification': {
                    'AntiPatternQuota': {
                        'policy1': {
                            'distributed': 1,     # XML parser "true" to 1
                            'Synchronous': 0      # XML parser "false" to 0
                        }
                    }
                }
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_anti_patterns()

        # Verify the complex lines with multiple invocations work with integers
        mock_sheet.write.assert_any_call(1, 3, 1)    # _safe_value(1)
        mock_sheet.write.assert_any_call(1, 4, 0)    # _safe_value(0)

    @patch('qualification_report.anti_patterns_mapping')
    def test_report_anti_patterns_with_dictionary_values(self, mock_mapping):
        """
        Test report_anti_patterns method with dictionary values
        (malformed XML parsing).
        """
        mock_mapping.__getitem__.side_effect = (
            self.anti_patterns_mapping.__getitem__)
        self.export_data['proxy_dependency_map'] = {
            'proxy1': {
                'qualification': {
                    'AntiPatternQuota': {
                        'policy1': {
                            'distributed': {
                                'nested_key': 'nested_value',
                                'another_key': 123
                            },
                            'Synchronous': True
                        }
                    }
                }
            }
        }
        report = QualificationReport(
            'test.xlsx',
            self.export_data,
            self.topology_mapping,
            self.cfg,
            self.backend_cfg,
            self.org_name
        )
        mock_sheet = Mock()
        self.mock_workbook.add_worksheet.return_value = mock_sheet
        report.report_anti_patterns()

        # Verify the complex lines handle dictionary values
        # (the customer's error scenario)
        expected_distributed = str({
            'nested_key': 'nested_value',
            'another_key': 123
        })
        mock_sheet.write.assert_any_call(1, 3, expected_distributed)
        mock_sheet.write.assert_any_call(1, 4, True)
