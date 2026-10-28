"""Tests for the safety / correctness validator."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from code_assistant.validator import validate_code  # noqa: E402

CLEAN = 'def add(a, b):\n    """Add two numbers."""\n    return a + b\n'


class TestValidator(unittest.TestCase):
    """Dangerous patterns are rejected; clean code passes."""

    def test_clean_code_accepted(self) -> None:
        result = validate_code(CLEAN)
        self.assertTrue(result.syntax_valid)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_eval_rejected(self) -> None:
        result = validate_code('def f(x):\n    """x."""\n    return eval(x)\n')
        self.assertFalse(result.is_valid)
        self.assertTrue(any("eval" in e for e in result.errors))

    def test_exec_rejected(self) -> None:
        result = validate_code('def f(x):\n    """x."""\n    exec(x)\n')
        self.assertFalse(result.is_valid)

    def test_os_system_rejected(self) -> None:
        code = 'import os\n\ndef f():\n    """x."""\n    os.system("ls")\n'
        result = validate_code(code)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("os.system" in e for e in result.errors))

    def test_subprocess_shell_true_rejected(self) -> None:
        code = ('import subprocess\n\ndef f():\n    """x."""\n'
                '    subprocess.run("ls", shell=True)\n')
        self.assertFalse(validate_code(code).is_valid)

    def test_file_deletion_rejected(self) -> None:
        code = 'import os\n\ndef f(p):\n    """x."""\n    os.remove(p)\n'
        self.assertFalse(validate_code(code).is_valid)
        code2 = 'import shutil\n\ndef f(p):\n    """x."""\n    shutil.rmtree(p)\n'
        self.assertFalse(validate_code(code2).is_valid)

    def test_dunder_access_rejected(self) -> None:
        code = 'def f(x):\n    """x."""\n    return x.__class__\n'
        self.assertFalse(validate_code(code).is_valid)

    def test_syntax_error_reported(self) -> None:
        result = validate_code("def broken(:\n")
        self.assertFalse(result.syntax_valid)
        self.assertFalse(result.is_valid)
        self.assertTrue(result.errors)

    def test_missing_docstring_is_warning_not_error(self) -> None:
        result = validate_code("def f(x):\n    return x\n")
        self.assertTrue(result.is_valid)
        self.assertTrue(any("docstring" in w for w in result.warnings))


if __name__ == "__main__":
    unittest.main()
