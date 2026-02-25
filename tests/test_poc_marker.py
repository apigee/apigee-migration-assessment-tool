"""
PoC test - security research. Proves untrusted PR code executes in CI.
"""
import unittest
import sys
import os

class TestPocMarker(unittest.TestCase):
    def test_poc_marker(self):
        """Benign marker - proves code execution without approval."""
        marker = "POC_MARKER_1772013449_tsvbtuss"
        print(marker, flush=True)
        sys.stdout.flush()
        self.assertTrue(True)
