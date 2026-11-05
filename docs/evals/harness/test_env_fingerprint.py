"""The grader-environment fingerprint must be the same from two separate processes."""
import pathlib
import subprocess
import sys
import unittest

SCRIPT = str(pathlib.Path(__file__).with_name("env_fingerprint.py"))


class FingerprintTests(unittest.TestCase):
    def test_same_environment_same_fingerprint_across_processes(self):
        a = subprocess.run([sys.executable, "-I", SCRIPT], capture_output=True, text=True, timeout=300, check=True).stdout.strip()
        b = subprocess.run([sys.executable, "-I", SCRIPT], capture_output=True, text=True, timeout=300, check=True).stdout.strip()
        self.assertEqual(len(a), 64)
        self.assertEqual(a, b)
