"""Offline tests for the actual PowerShell wrapper's Python preflight."""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(os.name == 'nt', 'Windows PowerShell environment check')
class PreflightEncodingTests(unittest.TestCase):
    def run_preflight(self, configuration):
        wrapper = (Path(__file__).parents[1] / 'scripts' / 'phase3c_prepare.ps1').read_text(encoding='utf-8')
        match = re.search(r'& \$python -I -c "(import os,sys,pathlib;.*?)" \$root', wrapper)
        self.assertIsNotNone(match, 'Could not find the actual environment check')
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            root = Path(d)
            venv = root / 'AI-Video-Workspace' / 'phase3b' / '.venv'
            venv.mkdir(parents=True)
            (venv / 'pyvenv.cfg').write_bytes(configuration)
            code = (f'import sys; sys.prefix={str(venv)!r}; sys.base_prefix="different"; '
                    f'sys.argv=["preflight",{str(root)!r}]; exec({match.group(1)!r})')
            return subprocess.run([sys.executable, '-I', '-X', 'utf8=0', '-c', code],
                                  capture_output=True, timeout=15)

    def test_utf8_configuration_with_chinese_path(self):
        config = 'include-system-site-packages = false\ncommand = 剪辑\n'.encode('utf-8')
        result = self.run_preflight(config)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))

    def test_system_site_packages_remain_blocked(self):
        config = 'include-system-site-packages = true\ncommand = 剪辑\n'.encode('utf-8')
        self.assertNotEqual(self.run_preflight(config).returncode, 0)

    def test_invalid_configuration_remains_blocked(self):
        config = b'include-system-site-packages = false\ncommand = \xff\n'
        self.assertNotEqual(self.run_preflight(config).returncode, 0)


if __name__ == '__main__':
    unittest.main()
