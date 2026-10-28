"""Tests for context retrieval and the token budget."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from code_assistant.context import build_context, estimate_tokens, rank_symbols  # noqa: E402
from code_assistant.indexer import index_codebase  # noqa: E402

SAMPLE = Path(__file__).resolve().parent.parent / "examples" / "sample_codebase"


class TestContext(unittest.TestCase):
    """Retrieval ranks the right symbol first and respects the budget."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = index_codebase(SAMPLE)

    def test_ranking_puts_relevant_symbol_first(self) -> None:
        ranked = rank_symbols(self.index, "count the words in a piece of text")
        self.assertGreater(ranked[0].score, 0)
        self.assertEqual(ranked[0].symbol.name, "count_words")

    def test_ranking_for_total_value(self) -> None:
        ranked = rank_symbols(self.index, "compute the total value of inventory items")
        names = [r.symbol.name for r in ranked if r.score > 0]
        self.assertIn("total_value", names[:2])

    def test_budget_is_respected(self) -> None:
        block = build_context(
            self.index, "add multiply divide average calculator numbers",
            token_budget=60,
        )
        self.assertLessEqual(block.token_count, 60)
        self.assertLessEqual(estimate_tokens(block.text), 60 + 5)

    def test_larger_budget_includes_more(self) -> None:
        small = build_context(self.index, "add numbers sum", token_budget=50)
        large = build_context(self.index, "add numbers sum", token_budget=2000)
        self.assertGreaterEqual(len(large.symbols), len(small.symbols))
        self.assertGreaterEqual(large.token_count, small.token_count)

    def test_estimate_tokens_positive(self) -> None:
        self.assertGreater(estimate_tokens("hello world"), 0)
        self.assertEqual(estimate_tokens(""), 0)


if __name__ == "__main__":
    unittest.main()
