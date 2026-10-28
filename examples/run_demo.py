"""End-to-end demo: index → retrieve context → generate → validate → test.

Run from the project root:

    python3 examples/run_demo.py

Everything is offline — generation uses the deterministic TemplateLLM.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from code_assistant import build_context, index_codebase, run_generated_code, validate_code  # noqa: E402
from code_assistant.llm import TemplateLLM  # noqa: E402
from code_assistant.prompts import build_generate_prompt  # noqa: E402

TEST_CODE = '''
import unittest

from solution import add


class TestAdd(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(add(2, 3), 5)

    def test_negative(self):
        self.assertEqual(add(-1, 1), 0)


if __name__ == "__main__":
    unittest.main()
'''


def main() -> int:
    """Run the full pipeline against the bundled sample codebase."""
    sample = PROJECT_ROOT / "examples" / "sample_codebase"

    print("== 1. Indexing sample codebase ==")
    index = index_codebase(sample)
    print(f"Modules: {sorted(index.modules)}")
    print(f"Symbols: {len(index.symbols)}")
    for module, deps in sorted(index.dependency_graph.items()):
        if deps:
            print(f"Dependency: {module} -> {sorted(deps)}")

    task = "Write a function `add(a, b)` that returns the sum of two numbers"
    print(f"\n== 2. Building context for: {task} ==")
    block = build_context(index, task, token_budget=400)
    print(f"Retrieved: {[s.qualname for s in block.symbols]}")
    print(f"Tokens: {block.token_count}/{block.token_budget}")

    print("\n== 3. Generating code (TemplateLLM, streamed) ==")
    prompt = build_generate_prompt(task, block.text)
    llm = TemplateLLM()
    chunks = list(llm.stream(prompt))
    code = "".join(chunks)
    print(f"(streamed in {len(chunks)} chunk(s))")
    print(code)

    print("== 4. Validating generated code ==")
    result = validate_code(code)
    print(f"Syntax valid: {result.syntax_valid} | Valid: {result.is_valid} "
          f"| Errors: {result.errors} | Warnings: {result.warnings}")
    if not result.is_valid:
        return 1

    print("== 5. Running the test harness ==")
    harness = run_generated_code(code, TEST_CODE, timeout=10)
    print(harness.output)
    print(f"Harness passed: {harness.passed}")
    return 0 if harness.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
