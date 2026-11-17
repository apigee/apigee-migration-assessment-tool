"""Tests for CI Apigee Edge access token TOTP generation."""

import importlib.util
import os
import unittest


def _load_ci_token_module():
    module_path = os.path.join(
        os.path.dirname(__file__),
        "ci",
        "generate_apigee_edge_access_token.py",
    )
    spec = importlib.util.spec_from_file_location(
        "generate_apigee_edge_access_token", module_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestGenerateApigeeEdgeAccessToken(unittest.TestCase):
    """Test cases for stdlib RFC 6238 TOTP generation."""

    @classmethod
    def setUpClass(cls):
        cls.token_mod = _load_ci_token_module()

    def test_rfc6238_sha1_vector(self):
        """Verify TOTP output matches RFC 6238 SHA-1 test vector at t=59."""
        # Key = b"12345678901234567890" -> GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ
        secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        self.assertEqual(
            self.token_mod.generate_totp(secret, digits=8, for_time=59),
            "94287082",
        )
        self.assertEqual(
            self.token_mod.generate_totp(secret, digits=6, for_time=59),
            "287082",
        )

    def test_short_80bit_secret_supported(self):
        """Verify 80-bit (16-char) secrets work without 112-bit error."""
        # Standard 80-bit test secret (16 Base32 chars = 10 bytes)
        code = self.token_mod.generate_totp("JBSWY3DPEHPK3PXP", for_time=0)
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_unpadded_spaced_lowercase_secret(self):
        """Verify whitespace and lowercase Base32 secrets are normalized."""
        a = self.token_mod.generate_totp("JBSWY3DPEHPK3PXP", for_time=123456)
        b = self.token_mod.generate_totp(
            " jbsw y3dp ehpk 3pxp ", for_time=123456
        )
        self.assertEqual(a, b)

    def test_empty_secret_raises(self):
        """Verify empty secrets raise ValueError."""
        with self.assertRaises(ValueError):
            self.token_mod.generate_totp("   ")


if __name__ == "__main__":
    unittest.main()
