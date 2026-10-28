"""Tests for the codebase indexer."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from code_assistant.indexer import index_codebase  # noqa: E402

SAMPLE = Path(__file__).resolve().parent.parent / "examples" / "sample_codebase"


class TestIndexer(unittest.TestCase):
    """Indexer extracts symbols, docstrings, signatures, and dep edges."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = index_codebase(SAMPLE)

    def test_modules_found(self) -> None:
        self.assertIn("sample_pkg.calculator", self.index.modules)
        self.assertIn("sample_pkg.text_utils", self.index.modules)
        self.assertIn("sample_pkg.inventory", self.index.modules)

    def test_function_symbol_extracted_with_docstring(self) -> None:
        add = self.index.get_symbol("sample_pkg.calculator.add")
        self.assertIsNotNone(add)
        assert add is not None
        self.assertEqual(add.kind, "function")
        self.assertIn("sum", add.docstring)
        self.assertIn("def add(a, b)", add.signature)

    def test_class_and_method_extracted(self) -> None:
        klass = self.index.get_symbol("sample_pkg.calculator.Calculator")
        self.assertIsNotNone(klass)
        assert klass is not None
        self.assertEqual(klass.kind, "class")
        method = self.index.get_symbol("sample_pkg.calculator.Calculator.add_to_total")
        self.assertIsNotNone(method)
        assert method is not None
        self.assertEqual(method.kind, "method")

    def test_dependency_graph_edges(self) -> None:
        graph = self.index.dependency_graph
        self.assertIn("sample_pkg.calculator", graph["sample_pkg.text_utils"])
        self.assertIn("sample_pkg.calculator", graph["sample_pkg.inventory"])
        self.assertEqual(graph["sample_pkg.calculator"], set())

    def test_dependents_reverse_lookup(self) -> None:
        dependents = self.index.dependents_of("sample_pkg.calculator")
        self.assertIn("sample_pkg.text_utils", dependents)
        self.assertIn("sample_pkg.inventory", dependents)


if __name__ == "__main__":
    unittest.main()
