"""Tests for the test harness and the offline TemplateLLM."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from code_assistant.harness import run_generated_code  # noqa: E402
from code_assistant.llm import TemplateLLM  # noqa: E402
from code_assistant.prompts import build_generate_prompt, build_refactor_prompt  # noqa: E402
from code_assistant.validator import validate_code  # noqa: E402

TEST_FOR_ADD = '''
import unittest

from solution import add


class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)


if __name__ == "__main__":
    unittest.main()
'''

GOOD_ADD = 'def add(a, b):\n    """Add."""\n    return a + b\n'
BAD_ADD = 'def add(a, b):\n    """Add (wrong)."""\n    return a - b\n'


class TestHarness(unittest.TestCase):
    """The harness passes correct code and fails wrong code."""

    def test_correct_snippet_passes(self) -> None:
        result = run_generated_code(GOOD_ADD, TEST_FOR_ADD, timeout=15)
        self.assertTrue(result.passed)
        self.assertEqual(result.returncode, 0)

    def test_wrong_snippet_fails(self) -> None:
        result = run_generated_code(BAD_ADD, TEST_FOR_ADD, timeout=15)
        self.assertFalse(result.passed)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL", result.output)

    def test_broken_snippet_fails(self) -> None:
        result = run_generated_code("def add(:\n", TEST_FOR_ADD, timeout=15)
        self.assertFalse(result.passed)


class TestTemplateLLM(unittest.TestCase):
    """TemplateLLM output compiles, validates, streams, and behaves."""

    def setUp(self) -> None:
        self.llm = TemplateLLM()

    def test_generate_add_compiles_and_validates(self) -> None:
        prompt = build_generate_prompt(
            "Write a function `add(a, b)` that returns the sum of two numbers"
        )
        code = self.llm.generate(prompt)
        compile(code, "<test>", "exec")  # raises if invalid syntax
        self.assertTrue(validate_code(code).is_valid)
        namespace: dict = {}
        exec(code, namespace)  # test-only: code is our own template output
        self.assertEqual(namespace["add"](2, 3), 5)
        self.assertEqual(namespace["add"](-1, 1), 0)

    def test_generate_multiply(self) -> None:
        prompt = build_generate_prompt(
            "Write a function `multiply(a, b)` that returns the product"
        )
        namespace: dict = {}
        exec(self.llm.generate(prompt), namespace)
        self.assertEqual(namespace["multiply"](3, 4), 12)

    def test_stream_reassembles_to_generate(self) -> None:
        prompt = build_generate_prompt(
            "Write a function `add(a, b)` that returns the sum"
        )
        streamed = "".join(self.llm.stream(prompt))
        self.assertEqual(streamed, self.llm.generate(prompt))
        self.assertIn("def add", streamed)

    def test_refactor_adds_docstrings(self) -> None:
        original = "def double(x):\n    return x * 2\n"
        prompt = build_refactor_prompt(original, "add missing docstrings")
        refactored = self.llm.generate(prompt)
        self.assertIn('"""', refactored)
        self.assertTrue(validate_code(refactored).is_valid)
        namespace: dict = {}
        exec(refactored, namespace)
        self.assertEqual(namespace["double"](21), 42)

    def test_determinism(self) -> None:
        prompt = build_generate_prompt(
            "Write a function `add(a, b)` that returns the sum"
        )
        self.assertEqual(self.llm.generate(prompt), self.llm.generate(prompt))


if __name__ == "__main__":
    unittest.main()
