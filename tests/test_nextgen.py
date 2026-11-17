"""Module docstring."""

import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

from nextgen import ApigeeNewGen


class TestApigeeNewGen(unittest.TestCase):
    """Test class for ApigeeNewGen."""

    def setUp(self):
        """Set up."""
        self.baseurl = "https://apigee.googleapis.com/v1"
        self.project_id = "test_project"
        self.token = "test_token"
        self.env_type = "hybrid"
        self.ssl_verify = True
        self.nextgen_client = ApigeeNewGen(self.baseurl, self.project_id,
                                           self.token, self.env_type,
                                           self.ssl_verify)
        self.nextgen_client.client = MagicMock()

    @patch('nextgen.Credentials')
    @patch('nextgen.resourcemanager_v3.ProjectsClient')
    def test_validate_permissions(self, mock_projects_client,
                                  mock_credentials):
        """Test validate permissions."""
        mock_credentials.return_value = "dummy_credentials"
        (mock_projects_client.return_value.
         test_iam_permissions.return_value.permissions) = ["permission1"]
        with patch('nextgen.parse_json') as mock_parse_json:
            mock_parse_json.return_value = ["permission1", "permission2"]
            missing = self.nextgen_client.validate_permissions()
            self.assertEqual(missing, ["permission2"])

    def test_get_org(self):
        """Test get org."""
        self.nextgen_client.client.get.return_value = {"name": "test_project"}
        result = self.nextgen_client.get_org()
        self.assertEqual(result, {"name": "test_project"})
        self.nextgen_client.client.get.assert_called_with(
            f"{self.baseurl}/organizations/{self.project_id}")

    def test_list_environments(self):
        """Test list environments."""
        with patch.object(self.nextgen_client,
                          'list_org_objects') as mock_list_org_objects:
            mock_list_org_objects.return_value = ["test", "prod"]
            result = self.nextgen_client.list_environments()
            self.assertEqual(result, ["test", "prod"])
            mock_list_org_objects.assert_called_with('environments')

    def test_list_org_objects_paginated(self):
        """Test list org objects paginated."""
        self.nextgen_client.client.get.side_effect = [
            {"developer": [{"email": "a@a.com"}, {"email": "b@b.com"}]},
            {"developer": [{"email": "b@b.com"}, {"email": "c@c.com"}]},
            {}
        ]
        result = self.nextgen_client.list_org_objects("developers")
        self.assertEqual(result, ["a@a.com", "b@b.com", "c@c.com"])

    def test_list_org_objects_not_paginated(self):
        """Test list org objects not paginated."""
        self.nextgen_client.client.get.return_value = [{"name": "test"},
                                                       {"name": "prod"}]
        result = self.nextgen_client.list_org_objects("environments")
        self.assertEqual(result, [{"name": "test"}, {"name": "prod"}])

    def test_list_org_objects_expand(self):
        """Test list org objects expand."""
        self.nextgen_client.client.get.side_effect = [
            {"apiProduct": [{"name": "p1"}, {"name": "p2"}]},
            {"apiProduct": [{"name": "p2"}, {"name": "p3"}]},
            {}
        ]
        result = self.nextgen_client.list_org_objects_expand("apiproducts")
        self.assertEqual(list(result.keys()), ["p1", "p2", "p3"])

    def test_get_org_object(self):
        """Test get org object."""
        self.nextgen_client.client.get.return_value = {
            "name": "test_developer"}
        result = self.nextgen_client.get_org_object("developers", "a@a.com")
        self.assertEqual(result, {"name": "test_developer"})

    def test_list_env_objects(self):
        """Test list env objects."""
        self.nextgen_client.client.get.return_value = ["target1", "target2"]
        result = self.nextgen_client.list_env_objects("test", "targetservers")
        self.assertEqual(result, ["target1", "target2"])

    def test_get_env_object(self):
        """Test get env object."""
        self.nextgen_client.client.get.return_value = {"name": "test_target"}
        result = self.nextgen_client.get_env_object("test", "targetservers",
                                                    "test_target")
        self.assertEqual(result, {"name": "test_target"})

    def test_list_env_groups(self):
        """Test list env groups."""
        with patch.object(
            self.nextgen_client,
                'list_org_objects_expand') as mock_list_org_objects_expand:
            mock_list_org_objects_expand.return_value = {"default": {}}
            result = self.nextgen_client.list_env_groups()
            self.assertEqual(result, {"default": {}})
            mock_list_org_objects_expand.assert_called_with('envgroups')

    def test_get_env_groups(self):
        """Test get env groups."""
        with patch.object(self.nextgen_client,
                          'get_org_object') as mock_get_org_object:
            mock_get_org_object.return_value = {"name": "default"}
            result = self.nextgen_client.get_env_groups("default")
            self.assertEqual(result, {"name": "default"})
            mock_get_org_object.assert_called_with('envgroups', 'default')

    def test_list_apis(self):
        """Test list apis."""
        with patch.object(self.nextgen_client,
                          'list_org_objects') as mock_list_org_objects:
            mock_list_org_objects.return_value = ["api1", "api2"]
            result = self.nextgen_client.list_apis("apis")
            self.assertEqual(result, ["api1", "api2"])
            mock_list_org_objects.assert_called_with('apis')

    def test_list_api_revisions(self):
        """Test list api revisions."""
        self.nextgen_client.client.get.return_value = ["1", "2"]
        result = self.nextgen_client.list_api_revisions("apis", "test_api")
        self.assertEqual(result, ["1", "2"])

    def test_api_env_mapping(self):
        """Test api env mapping."""
        self.nextgen_client.client.get.return_value = {
            "deployments": [{"environment": "test", "revision": "1"}]}
        result = self.nextgen_client.api_env_mapping("apis", "test_api")
        self.assertEqual(
            result,
            {'environment': [{'name': 'test', 'revision': [{'name': '1'}]}]})

    def test_list_apis_env(self):
        """Test list apis env."""
        self.nextgen_client.client.get.return_value = {
            "deployments": [{"apiProxy": "api1"}, {"apiProxy": "api2"}]}
        result = self.nextgen_client.list_apis_env("test")
        self.assertEqual(result, ["api1", "api2"])

    @patch("builtins.open", new_callable=mock_open, read_data=b"data")
    def test_fetch_api_revision(self, mock_file):
        """Test fetch api revision."""
        self.nextgen_client.client.file_get.return_value = b"bundle_data"
        self.nextgen_client.fetch_api_revision("apis", "test_api", "1",
                                               "export_dir")
        expected_path = os.path.abspath(
            os.path.join("export_dir", "test_api.zip")
        )
        mock_file.assert_called_with(expected_path, "wb")
        mock_file().write.assert_called_with(b"bundle_data")

    def test_write_proxy_bundle_blocks_traversal(self):
        """Test _write_proxy_bundle rejects path traversal names."""
        for bad_name in ["../../evil", "dir/proxy", "dir\\proxy", "..", ""]:
            with self.assertRaises(ValueError):
                self.nextgen_client._write_proxy_bundle(  # noqa pylint: disable=W0212
                    "export_dir", bad_name, b"data"
                )

    @patch('nextgen.RestClient')
    def test_googleapis_enforces_ssl_verify(self, mock_rest_client):
        """Test googleapis.com endpoints enforce ssl_verify=True."""
        ApigeeNewGen(
            "https://apigee.googleapis.com/v1",
            "proj",
            "tok",
            "hybrid",
            False,
        )
        mock_rest_client.assert_called_once_with('oauth', 'tok', True)

    @patch("builtins.open", new_callable=mock_open, read_data=b"data")
    def test_create_api(self, _):
        """Test create api."""
        self.nextgen_client.client.file_post.return_value = {
            "name": "test_api"}
        result = self.nextgen_client.create_api("apis", "test_api",
                                                "bundle.zip", "create")
        self.assertEqual(result, {"name": "test_api"})


if __name__ == '__main__':
    unittest.main()
