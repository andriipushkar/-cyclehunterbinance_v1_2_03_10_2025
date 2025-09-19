import os
import json
import unittest
from cli_monitor.arbitrage.configurator import (
    create_default_config_files, 
    CONFIG_DIR, 
    CONFIG_FILE, 
    MONITORED_COINS_FILE, 
    DEFAULT_CONFIG, 
    DEFAULT_MONITORED_COINS
)

class TestConfigurator(unittest.TestCase):

    def setUp(self):
        """Set up test environment."""
        self.config_dir = CONFIG_DIR
        self.config_file = CONFIG_FILE
        self.monitored_coins_file = MONITORED_COINS_FILE
        self._cleanup()

    def tearDown(self):
        """Clean up after tests."""
        self._cleanup()

    def _cleanup(self):
        """Remove created files and directory."""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        if os.path.exists(self.monitored_coins_file):
            os.remove(self.monitored_coins_file)
        if os.path.exists(self.config_dir):
            # Check if directory is empty before removing
            if not os.listdir(self.config_dir):
                os.rmdir(self.config_dir)

    def test_create_default_config_files_creation(self):
        """Test that config files are created correctly."""
        # Ensure files and directory don't exist before running
        self.assertFalse(os.path.exists(self.config_file))
        self.assertFalse(os.path.exists(self.monitored_coins_file))

        # Run the function
        create_default_config_files()

        # Check directory and files exist
        self.assertTrue(os.path.exists(self.config_dir))
        self.assertTrue(os.path.exists(self.config_file))
        self.assertTrue(os.path.exists(self.monitored_coins_file))

        # Check content of config.json
        with open(self.config_file, 'r') as f:
            config_data = json.load(f)
        self.assertEqual(config_data, DEFAULT_CONFIG)

        # Check content of monitored_coins.json
        with open(self.monitored_coins_file, 'r') as f:
            monitored_coins_data = json.load(f)
        self.assertEqual(monitored_coins_data, DEFAULT_MONITORED_COINS)

    def test_create_default_config_files_idempotent(self):
        """Test that running the function again does not change existing files."""
        # Create files first
        create_default_config_files()

        # Get modification times
        config_mtime = os.path.getmtime(self.config_file)
        coins_mtime = os.path.getmtime(self.monitored_coins_file)

        # Run the function again to ensure it doesn't overwrite
        create_default_config_files()

        # Check that modification times have not changed
        self.assertEqual(os.path.getmtime(self.config_file), config_mtime)
        self.assertEqual(os.path.getmtime(self.monitored_coins_file), coins_mtime)

if __name__ == '__main__':
    unittest.main()
