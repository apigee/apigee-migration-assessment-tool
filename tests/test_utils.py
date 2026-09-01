"""Test suite for utils."""
import json
import os
import shutil
import unittest
import zipfile
from configparser import ConfigParser
from unittest.mock import MagicMock, mock_open, patch
import utils


# pylint: disable=too-many-public-methods
class TestUtils(unittest.TestCase):
    """Test class for utils."""

    def setUp(self):
        """Set up."""
        self.test_dir = "test_dir"
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        """Tear down."""
        shutil.rmtree(self.test_dir)

    def test_parse_config(self):
        """Test parse config."""
        config_content = "[test]\nkey=value"
        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("configparser.ConfigParser.read"):
                with patch("configparser.ConfigParser.sections",
                           return_value=["test"]):
                    config = utils.parse_config("dummy_path")
                    self.assertIsInstance(config, ConfigParser)

    def test_get_env_variable(self):
        """Test get env variable."""
        with patch.dict(os.environ, {"TEST_KEY": "test_value"}):
            self.assertEqual(utils.get_env_variable("TEST_KEY"), "test_value")
        self.assertIsNone(utils.get_env_variable("NON_EXISTENT_KEY"))

    @patch("requests.get")
    def test_is_token_valid(self, mock_get):
        """Test is token valid."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"email": "test@example.com"}
        mock_get.return_value = mock_response
        self.assertTrue(utils.is_token_valid("valid_token"))

        mock_response.status_code = 400
        self.assertFalse(utils.is_token_valid("invalid_token"))

    @patch('utils.is_token_valid', return_value=True)
    def test_get_access_token(self, _):
        """Test get access token."""
        with patch.dict(os.environ, {'APIGEE_ACCESS_TOKEN': 'test_token'}):
            self.assertEqual(utils.get_access_token(), 'test_token')

    @patch('sys.exit')
    @patch('utils.is_token_valid', return_value=False)
    def test_get_access_token_invalid(self, _, mock_exit):
        """Test get access token invalid."""
        with patch.dict(os.environ, {'APIGEE_ACCESS_TOKEN': 'test_token'}):
            utils.get_access_token()
            mock_exit.assert_called_with(1)

    def test_get_source_auth_token(self):
        """Test get source auth token."""
        with patch.dict(os.environ, {'SOURCE_AUTH_TOKEN': 'test_token'}):
            self.assertEqual(utils.get_source_auth_token(), 'test_token')

    @patch('sys.exit')
    def test_get_source_auth_token_not_set(self, mock_exit):
        """Test get source auth token not set."""
        with patch.dict(os.environ, {}, clear=True):
            utils.get_source_auth_token()
            mock_exit.assert_called_with(1)

    def test_create_dir(self):
        """Test create dir."""
        dir_path = os.path.join(self.test_dir, "new_dir")
        utils.create_dir(dir_path)
        self.assertTrue(os.path.exists(dir_path))

    def test_list_dir(self):
        """Test list dir."""
        test_subdir = os.path.join(self.test_dir, "list_dir_test")
        os.makedirs(test_subdir)
        file_path = os.path.join(test_subdir, "test_file.txt")
        with open(file_path, "w", encoding='utf-8') as f:
            f.write("test")
        self.assertEqual(utils.list_dir(test_subdir), ["test_file.txt"])

    def test_delete_folder(self):
        """Test delete folder."""
        dir_path = os.path.join(self.test_dir, "delete_me")
        os.makedirs(dir_path)
        utils.delete_folder(dir_path)
        self.assertFalse(os.path.exists(dir_path))

    @patch('utils.logger.info')
    def test_print_json(self, mock_logger_info):
        """Test print json."""
        test_data = {"key": "value"}
        utils.print_json(test_data)
        mock_logger_info.assert_called_with(json.dumps(test_data, indent=2))

    def test_parse_json(self):
        """Test parse json."""
        json_content = '{"key": "value"}'
        with patch("builtins.open", mock_open(read_data=json_content)):
            self.assertEqual(utils.parse_json("dummy.json"), {"key": "value"})

    def test_write_json(self):
        """Test write json."""
        file_path = os.path.join(self.test_dir, "test.json")
        data = {"key": "value"}
        utils.write_json(file_path, data)
        with open(file_path, "r", encoding='utf-8') as f:
            self.assertEqual(json.load(f), data)

    def test_read_file(self):
        """Test read file."""
        file_path = os.path.join(self.test_dir, "test.txt")
        content = b"hello world"
        with open(file_path, "wb") as f:
            f.write(content)
        self.assertEqual(utils.read_file(file_path), content)

    def test_write_file(self):
        """Test write file."""
        file_path = os.path.join(self.test_dir, "test_write.txt")
        data = b"some data"
        utils.write_file(file_path, data)
        with open(file_path, "rb") as f:
            self.assertEqual(f.read(), data)

    def test_compare_hash(self):
        """Test compare hash."""
        self.assertTrue(utils.compare_hash(b"data1", b"data1"))
        self.assertFalse(utils.compare_hash(b"data1", b"data2"))

    def test_get_proxy_endpoint_count(self):
        """Test get proxy endpoint count."""
        config = ConfigParser()
        config['unifier'] = {'proxy_endpoint_count': '5'}
        config['inputs'] = {'MAX_PROXY_ENDPOINT_LIMIT': '10'}
        self.assertEqual(utils.get_proxy_endpoint_count(config), 5)

    @patch('sys.exit')
    def test_get_proxy_endpoint_count_negative(self, mock_exit):
        """Test get proxy endpoint count negative."""
        config = ConfigParser()
        config['unifier'] = {'proxy_endpoint_count': '-1'}
        config['inputs'] = {'MAX_PROXY_ENDPOINT_LIMIT': '10'}
        utils.get_proxy_endpoint_count(config)
        mock_exit.assert_called_with(1)

    @patch('sys.exit')
    def test_get_proxy_endpoint_count_exceeds_limit(self, mock_exit):
        """Test get proxy endpoint count exceeds limit."""
        config = ConfigParser()
        config['unifier'] = {'proxy_endpoint_count': '11'}
        config['inputs'] = {'MAX_PROXY_ENDPOINT_LIMIT': '10'}
        utils.get_proxy_endpoint_count(config)
        mock_exit.assert_called_with(1)

    @patch('sys.exit')
    def test_get_proxy_endpoint_count_value_error(self, mock_exit):
        """Test get proxy endpoint count value error."""
        config = ConfigParser()
        config['unifier'] = {'proxy_endpoint_count': 'abc'}
        config['inputs'] = {'MAX_PROXY_ENDPOINT_LIMIT': '10'}
        utils.get_proxy_endpoint_count(config)
        mock_exit.assert_called_with(1)

    def test_generate_env_groups_tfvars(self):
        """Test generate env groups tfvars."""
        project_id = "test-project"
        env_config = {
            "prod": {
                "vhosts": {
                    "secure": {
                        "hostAliases": ["api.example.com"]
                    }
                }
            }
        }
        expected_tfvars = {
            'project_id': 'test-project',
            'envgroups': {
                'prod-secure': ['api.example.com']
            },
            'environments': {
                'prod': {
                    'display_name': 'prod',
                    'description': 'Apis for environment prod',
                    'envgroups': ['prod-secure']
                }
            }
        }
        self.assertEqual(
            utils.generate_env_groups_tfvars(project_id, env_config),
            expected_tfvars)

    def test_write_csv_report(self):
        """Test write csv report."""
        file_path = os.path.join(self.test_dir, "report.csv")
        header = ["col1", "col2"]
        rows = [["a", "b"], ["c", "d"]]
        utils.write_csv_report(file_path, header, rows)
        with open(file_path, "r", encoding='utf-8') as f:
            lines = f.readlines()
            self.assertEqual(lines[0].strip(), "col1,col2")
            self.assertEqual(lines[1].strip(), "a,b")
            self.assertEqual(lines[2].strip(), "c,d")

    def test_get_proxy_entrypoint(self):
        """Test get proxy entrypoint."""
        xml_file = os.path.join(self.test_dir, "proxy.xml")
        with open(xml_file, "w", encoding='utf-8') as f:
            f.write("<APIProxy/>")
        self.assertEqual(utils.get_proxy_entrypoint(self.test_dir), xml_file)

    def test_parse_xml(self):
        """Test parse xml."""
        xml_content = "<root><key>value</key></root>"
        with patch("builtins.open", mock_open(read_data=xml_content)):
            self.assertEqual(utils.parse_xml("dummy.xml"),
                             {"root": {"key": "value"}})

    def test_get_proxy_files(self):
        """Test get proxy files."""
        proxies_dir = os.path.join(self.test_dir, "proxies")
        os.makedirs(proxies_dir)
        with open(os.path.join(proxies_dir, "a.xml"), "w",
                  encoding='utf-8') as f:
            f.write("<root/>")
        with open(os.path.join(proxies_dir, "b.xml"), "w",
                  encoding='utf-8') as f:
            f.write("<root/>")
        self.assertEqual(sorted(utils.get_proxy_files(self.test_dir)),
                         sorted(["a", "b"]))

    def test_delete_file(self):
        """Test delete file."""
        file_path = os.path.join(self.test_dir, "delete_me.txt")
        with open(file_path, "w", encoding='utf-8') as f:
            f.write("test")
        utils.delete_file(file_path)
        self.assertFalse(os.path.exists(file_path))

    def test_write_xml_from_dict(self):
        """Test write xml from dict."""
        file_path = os.path.join(self.test_dir, "test.xml")
        data = {"root": {"key": "value"}}
        utils.write_xml_from_dict(file_path, data)
        with open(file_path, "r", encoding='utf-8') as f:
            content = f.read()
            self.assertIn("<root>", content)
            self.assertIn("<key>value</key>", content)
            self.assertIn("</root>", content)

    def test_copy_folder(self):
        """Test copy folder."""
        src_dir = os.path.join(self.test_dir, "src")
        dst_dir = os.path.join(self.test_dir, "dst")
        os.makedirs(src_dir)
        with open(os.path.join(src_dir, "test.txt"), "w",
                  encoding='utf-8') as f:
            f.write("test")
        utils.copy_folder(src_dir, dst_dir)
        self.assertTrue(os.path.exists(dst_dir))
        self.assertTrue(os.path.exists(os.path.join(dst_dir, "test.txt")))

    def test_clean_up_artifacts(self):
        """Test clean up artifacts."""
        target_dir = os.path.join(self.test_dir, "artifacts")
        os.makedirs(target_dir, exist_ok=True)
        with open(os.path.join(target_dir, "a.xml"), "w",
                  encoding='utf-8') as f:
            f.write("<root/>")
        with open(os.path.join(target_dir, "b.xml"), "w",
                  encoding='utf-8') as f:
            f.write("<root/>")
        utils.clean_up_artifacts(target_dir, ["a"])
        self.assertTrue(os.path.exists(os.path.join(target_dir, "a.xml")))
        self.assertFalse(os.path.exists(os.path.join(target_dir, "b.xml")))

    def test_filter_objects(self):
        """Test filter objects."""
        obj_data = {"Policy": ["a", "b", "c"]}
        self.assertEqual(utils.filter_objects(obj_data, "Policy", ["a", "c"]),
                         {"Policy": ["a", "c"]})
        self.assertEqual(utils.filter_objects(obj_data, "Policy", ["d"]),
                         {"Policy": []})

    def test_zipdir(self):
        """Test zipdir."""
        zip_path = os.path.join(self.test_dir, "test.zip")
        with open(os.path.join(self.test_dir, "file1.txt"), "w",
                  encoding='utf-8') as f:
            f.write("file1")
        sub_dir = os.path.join(self.test_dir, "sub")
        os.makedirs(sub_dir)
        with open(os.path.join(sub_dir, "file2.txt"), "w",
                  encoding='utf-8') as f:
            f.write("file2")

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            utils.zipdir(self.test_dir, zipf)

        with zipfile.ZipFile(zip_path, 'r') as zipf:
            self.assertEqual(len(zipf.namelist()),
                             3)
            self.assertIn('test_dir/file1.txt', zipf.namelist())
            self.assertIn('test_dir/sub/file2.txt', zipf.namelist())

    @patch('utils.copy_folder')
    @patch('utils.get_proxy_entrypoint')
    @patch('utils.parse_proxy_root')
    @patch('utils.delete_file')
    @patch('utils.filter_objects')
    @patch('utils.clean_up_artifacts')
    @patch('utils.write_xml_from_dict')
    @patch('zipfile.ZipFile')
    # noqa pylint: disable=too-many-arguments, too-many-locals, unused-argument, too-many-positional-arguments
    def test_clone_proxies(self, mock_zipfile, mock_write_xml, mock_clean_up,
                           mock_filter, mock_delete_file, mock_parse,
                           mock_get_entrypoint, mock_copy):
        """Test clone proxies."""
        source_dir = "source"
        target_dir = "target"
        objects = {
            "Name": "test_proxy",
            "Policies": ["policy1"],
            "TargetEndpoints": ["target1"],
            "ProxyEndpoints": ["proxy1"]
        }
        merged_pes = {"proxy1": {"ProxyEndpoint": {}}}
        proxy_bundle_directory = "bundles"

        mock_get_entrypoint.return_value = "source/apiproxy/test_proxy.xml"
        mock_parse.return_value = {
            "APIProxy": {
                "@name": "old_name",
                "Policies": {"Policy": ["policy1", "policy2"]},
                "TargetEndpoints": {"TargetEndpoint": ["target1", "target2"]},
                "ProxyEndpoints": {"ProxyEndpoint": ["proxy1", "proxy2"]}
            }
        }
        mock_filter.side_effect = [
            {"Policy": ["policy1"]},
            {"TargetEndpoint": ["target1"]}
        ]

        utils.clone_proxies(
                source_dir, target_dir, objects, merged_pes,
                proxy_bundle_directory
                )
        mock_copy.assert_called_with(source_dir, f"{target_dir}/apiproxy")
        mock_write_xml.assert_called()
        self.assertEqual(mock_clean_up.call_count, 3)
        self.assertEqual(mock_filter.call_count, 2)
        (mock_zipfile.assert_called_with(
            f"{proxy_bundle_directory}/test_proxy.zip",
            'w',
            zipfile.ZIP_DEFLATED))

    def test_safe_join_path(self):
        """Test safe_join_path prevents path traversal."""
        base_dir = "/app/target/export"
        # Normal safe join
        result = utils.safe_join_path(base_dir, "resourceFiles", "jsc", "test.js")
        self.assertEqual(
            result, os.path.abspath("/app/target/export/resourceFiles/jsc/test.js")
        )

        # Path traversal attempts
        with self.assertRaises(ValueError):
            utils.safe_join_path(base_dir, "..", "evil.txt")

        with self.assertRaises(ValueError):
            utils.safe_join_path(base_dir, "resourceFiles", "../../../etc/passwd")

        with self.assertRaises(ValueError):
            utils.safe_join_path(base_dir, "/etc/shadow")

    def test_sanitize_filename(self):
        """Test sanitize_filename strips path traversal and invalid characters."""
        self.assertEqual(utils.sanitize_filename("test.js"), "test.js")
        self.assertEqual(utils.sanitize_filename("../../etc/passwd"), "passwd")
        self.assertEqual(utils.sanitize_filename("/var/log/app.log"), "app.log")
        self.assertEqual(utils.sanitize_filename(".."), "")
        self.assertEqual(utils.sanitize_filename("."), "")
        self.assertEqual(utils.sanitize_filename(""), "")
        self.assertEqual(utils.sanitize_filename(None), "")
        self.assertEqual(utils.sanitize_filename("test\x00.js"), "test.js")


if __name__ == "__main__":
    unittest.main()
