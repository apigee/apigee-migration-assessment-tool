import unittest
from unittest.mock import patch, mock_open, MagicMock
import configparser
import sys
import os

# Add the 'scripts' directory to the Python path to allow importing 'setup'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))
import setup

class TestSetupScript(unittest.TestCase):

    # Decorators are applied bottom-up. The arguments to the test method
    # must match the reverse order of the decorators.
    def test_setup_interactive_first_run(self):
        """
        Tests the interactive setup flow for a fresh clone.
        """
        with patch('sys.argv', ['setup.py']) as mock_argv, \
             patch('builtins.input', side_effect=['test-user@example.com', 'test-password', 'test-org']) as mock_input, \
             patch('os.path.exists', return_value=False) as mock_exists, \
             patch('builtins.open', new_callable=mock_open, read_data='[inputs]\n') as mock_open_file, \
             patch('shutil.copy'), \
             patch('os.makedirs'):
            setup.main()
            handle_env = mock_open_file()
            mock_open_file.assert_any_call('input.properties', 'w')

    def test_setup_non_interactive_first_run(self):
        """
        Tests the non-interactive setup flow for a fresh clone.
        """
        with patch('sys.argv', ['setup.py', '-o', 'test-org']), \
             patch('os.path.exists', return_value=False), \
             patch('builtins.open', new_callable=mock_open, read_data='[inputs]\n') as mock_open_file, \
             patch('shutil.copy'), \
             patch('os.makedirs'):
            setup.main()
            mock_open_file.assert_any_call('input.properties', 'w')

    def test_setup_interactive_update(self):
        """
        Tests that the script correctly prompts for and updates an existing config.
        """
        with patch('sys.argv', ['setup.py']), \
             patch('builtins.input', side_effect=['new-test-org']), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', new_callable=mock_open, read_data='[inputs]\nsource_org = sample-saas-project-1'.encode()), \
             patch('configparser.ConfigParser') as mock_config_parser:
            mock_config_instance = MagicMock()
            mock_config_instance.get.return_value = 'sample-saas-project-1'
            mock_config_parser.return_value = mock_config_instance
            setup.main()
            mock_config_instance.set.assert_called_with('inputs', 'SOURCE_ORG', 'new-test-org')
            mock_config_instance.write.assert_called()

if __name__ == '__main__':
    unittest.main()