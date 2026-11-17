
"""
Tests for the classic module.
"""
import os
import unittest
from unittest.mock import MagicMock, patch

from classic import ApigeeClassic


class TestApigeeClassic(unittest.TestCase):
    """
    Test cases for the ApigeeClassic class.
    """

    def setUp(self):
        """
        Set up the test case.
        """
        self.baseurl = "https://api.enterprise.apigee.com/v1"
        self.org = "test_org"
        self.token = "test_token"
        self.auth_type = "oauth"
        self.ssl_verify = True
        self.classic_client = ApigeeClassic(self.baseurl, self.org, self.token,
                                            self.auth_type, self.ssl_verify)
        self.classic_client.client = MagicMock()

    def test_get_org(self):
        """
        Test the get_org method.
        """
        self.classic_client.client.get.return_value = {"name": "test_org"}
        result = self.classic_client.get_org()
        self.assertEqual(result, {"name": "test_org"})
        self.classic_client.client.get.assert_called_with(
            f"{self.baseurl}/organizations/{self.org}")

    def test_list_environments(self):
        """
        Test the list_environments method.
        """
        self.classic_client.client.get.return_value = ["test", "prod"]
        result = self.classic_client.list_environments()
        self.assertEqual(result, ["test", "prod"])
        self.classic_client.client.get.assert_called_with(
            f"{self.baseurl}/organizations/{self.org}/environments")

    def test_list_org_objects_paginated(self):
        """
        Test the list_org_objects method with paginated results.
        """
        self.classic_client.client.get.side_effect = [
            ["item1", "item2"],
            ["item2", "item3"],
            []
        ]
        result = self.classic_client.list_org_objects("apis")
        self.assertEqual(result, ["item1", "item2", "item3"])

    def test_list_org_objects_not_paginated(self):
        """
        Test the list_org_objects method with non-paginated results.
        """
        self.classic_client.client.get.return_value = ["item1", "item2"]
        result = self.classic_client.list_org_objects("kvms")
        self.assertEqual(result, ["item1", "item2"])

    def test_list_org_objects_expand(self):
        """
        Test the list_org_objects_expand method.
        """
        self.classic_client.client.get.side_effect = [
            {"app": [{"appId": "1"}, {"appId": "2"}]},
            {"app": [{"appId": "2"}, {"appId": "3"}]},
            {}
        ]
        result = self.classic_client.list_org_objects_expand("apps")
        self.assertEqual(list(result.keys()), ["1", "2", "3"])

    def test_get_org_object(self):
        """
        Test the get_org_object method.
        """
        self.classic_client.client.get.return_value = {"name": "test_object"}
        result = self.classic_client.get_org_object("developers",
                                                    "test_developer")
        self.assertEqual(result, {"name": "test_object"})

    def test_get_org_object_resourcefiles(self):
        """
        Test the get_org_object method for resourcefiles.
        """
        self.classic_client.client.get.return_value = "resource_data"
        result = self.classic_client.get_org_object(
            "resourcefiles", {"type": "jsc", "name": "test.js"})
        self.assertEqual(result, "resource_data")

    def test_list_env_objects(self):
        """
        Test the list_env_objects method.
        """
        self.classic_client.client.get.return_value = ["target1", "target2"]
        result = self.classic_client.list_env_objects("test", "targetservers")
        self.assertEqual(result, ["target1", "target2"])

    def test_get_env_object(self):
        """
        Test the get_env_object method.
        """
        self.classic_client.client.get.return_value = {"name": "test_target"}
        result = self.classic_client.get_env_object("test", "targetservers",
                                                    "test_target")
        self.assertEqual(result, {"name": "test_target"})

    def test_list_env_vhosts(self):
        """
        Test the list_env_vhosts method.
        """
        self.classic_client.client.get.return_value = ["default", "secure"]
        result = self.classic_client.list_env_vhosts("test")
        self.assertEqual(result, ["default", "secure"])

    def test_get_env_vhost(self):
        """
        Test the get_env_vhost method.
        """
        self.classic_client.client.get.return_value = {"name": "secure"}
        result = self.classic_client.get_env_vhost("test", "secure")
        self.assertEqual(result, {"name": "secure"})

    def test_list_apis(self):
        """
        Test the list_apis method.
        """
        self.classic_client.client.get.return_value = ["api1", "api2"]
        result = self.classic_client.list_apis("apis")
        self.assertEqual(result, ["api1", "api2"])

    def test_list_api_revisions(self):
        """
        Test the list_api_revisions method.
        """
        self.classic_client.client.get.return_value = ["1", "2"]
        result = self.classic_client.list_api_revisions("apis", "test_api")
        self.assertEqual(result, ["1", "2"])

    def test_api_env_mapping(self):
        """
        Test the api_env_mapping method.
        """
        self.classic_client.client.get.return_value = {"environment": [
            {"name": "test"}]}
        result = self.classic_client.api_env_mapping("apis", "test_api")
        self.assertEqual(result, {"environment": [{"name": "test"}]})

    def test_list_apis_env(self):
        """
        Test the list_apis_env method.
        """
        self.classic_client.client.get.return_value = {
            "aPIProxy": [{"name": "api1"}, {"name": "api2"}]}
        result = self.classic_client.list_apis_env("test")
        self.assertEqual(result, ["api1", "api2"])

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    def test_fetch_api_revision(self, mock_open):
        """
        Test the fetch_api_revision method.
        """
        self.classic_client.client.file_get.return_value = b"test_bundle_data"
        self.classic_client.fetch_api_revision("apis", "test_api", "1",
                                               "export_dir")
        expected_path = os.path.abspath(
            os.path.join("export_dir", "test_api.zip")
        )
        mock_open.assert_called_with(expected_path, "wb")
        mock_open().write.assert_called_with(b"test_bundle_data")

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    def test_write_proxy_bundle(self, mock_open):
        """
        Test the write_proxy_bundle method.
        """
        self.classic_client.write_proxy_bundle("export_dir", "test_api",
                                               b"test_data")
        expected_path = os.path.abspath(
            os.path.join("export_dir", "test_api.zip")
        )
        mock_open.assert_called_with(expected_path, "wb")
        mock_open().write.assert_called_with(b"test_data")

    def test_write_proxy_bundle_blocks_traversal(self):
        """Test write_proxy_bundle rejects path traversal names."""
        for bad_name in ["../../evil", "dir/proxy", "dir\\proxy", "..", ""]:
            with self.assertRaises(ValueError):
                self.classic_client.write_proxy_bundle(
                    "export_dir", bad_name, b"data"
                )

    @patch.object(ApigeeClassic, 'list_api_revisions')
    @patch.object(ApigeeClassic, 'fetch_api_revision')
    def test_fetch_proxy(self, mock_fetch_api_revision,
                         mock_list_api_revisions):
        """
        Test the fetch_proxy method.
        """
        mock_list_api_revisions.return_value = ["1", "2"]
        self.classic_client.fetch_proxy(("apis", "test_api", "export_dir"))
        mock_list_api_revisions.assert_called_with("apis", "test_api")
        mock_fetch_api_revision.assert_called_with("apis", "test_api", "2",
                                                   "export_dir")

    def test_view_pod_component_details(self):
        """
        Test the view_pod_component_details method.
        """
        self.classic_client.client.get.return_value = [{"uUID": "1234"}]
        result = self.classic_client.view_pod_component_details("gateway")
        self.assertEqual(result, [{"uUID": "1234"}])


if __name__ == '__main__':
    unittest.main()
