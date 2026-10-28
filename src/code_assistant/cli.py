"""Command-line interface: index / generate / refactor / explain.

All commands work fully offline with :class:`TemplateLLM`::

    code-assistant index examples/sample_codebase
    code-assistant generate "Write a function `add(a, b)` that returns the sum" \
        --codebase examples/sample_codebase
    code-assistant refactor path/to/file.py "add missing docstrings"
    code-assistant explain path/to/file.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .context import build_context
from .indexer import index_codebase
from .llm import TemplateLLM
from .prompts import (
    build_explain_prompt,
    build_generate_prompt,
    build_refactor_prompt,
)
from .validator import validate_code


def _cmd_index(args: argparse.Namespace) -> int:
    index = index_codebase(args.path)
    print(f"Indexed {len(index.modules)} module(s), {len(index.symbols)} symbol(s)")
    for name, module in sorted(index.modules.items()):
        print(f"\n{name}  ({module.path})")
        for symbol in module.symbols:
            print(f"  - {symbol.kind}: {symbol.signature}")
        deps = sorted(index.dependency_graph.get(name, set()))
        if deps:
            print(f"  depends on: {', '.join(deps)}")
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    context_text = ""
    if args.codebase:
        block = build_context(index_codebase(args.codebase), args.task,
                              token_budget=args.budget)
        context_text = block.text
        print(f"# context: {len(block.symbols)} symbol(s), "
              f"{block.token_count}/{args.budget} tokens", file=sys.stderr)
    prompt = build_generate_prompt(args.task, context_text)
    llm = TemplateLLM()
    if args.stream:
        for chunk in llm.stream(prompt):  # streaming generation interface
            print(chunk, end="")
        print()
        return 0
    code = llm.generate(prompt)
    print(code)
    result = validate_code(code)
    status = "VALID" if result.is_valid else f"INVALID: {result.errors}"
    print(f"# validation: {status} (warnings: {result.warnings})", file=sys.stderr)
    return 0 if result.is_valid else 1


def _cmd_refactor(args: argparse.Namespace) -> int:
    code = Path(args.file).read_text(encoding="utf-8")
    context_text = ""
    if args.codebase:
        block = build_context(index_codebase(args.codebase), args.instruction)
        context_text = block.text
    prompt = build_refactor_prompt(code, args.instruction, context_text)
    refactored = TemplateLLM().generate(prompt)
    print(refactored)
    result = validate_code(refactored)
    status = "VALID" if result.is_valid else f"INVALID: {result.errors}"
    print(f"# validation: {status}", file=sys.stderr)
    return 0 if result.is_valid else 1


def _cmd_explain(args: argparse.Namespace) -> int:
    code = Path(args.file).read_text(encoding="utf-8")
    prompt = build_explain_prompt(code)
    print(TemplateLLM().generate(prompt))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser (kept separate for testability)."""
    parser = argparse.ArgumentParser(
        prog="code-assistant",
        description="Generate and refactor Python code, safely, offline.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="Index a Python codebase")
    p_index.add_argument("path", help="Directory to index")
    p_index.set_defaults(func=_cmd_index)

    p_gen = sub.add_parser("generate", help="Generate code from a task")
    p_gen.add_argument("task", help='e.g. "Write a function `add(a, b)` '
                                    'that returns the sum"')
    p_gen.add_argument("--codebase", default=None,
                       help="Codebase to retrieve context from")
    p_gen.add_argument("--budget", type=int, default=1200,
                       help="Context token budget (default: 1200)")
    p_gen.add_argument("--stream", action="store_true",
                       help="Stream the output chunk by chunk")
    p_gen.set_defaults(func=_cmd_generate)

    p_ref = sub.add_parser("refactor", help="Refactor a Python file")
    p_ref.add_argument("file", help="Python file to refactor")
    p_ref.add_argument("instruction", help="What to change")
    p_ref.add_argument("--codebase", default=None)
    p_ref.set_defaults(func=_cmd_refactor)

    p_exp = sub.add_parser("explain", help="Explain a Python file")
    p_exp.add_argument("file", help="Python file to explain")
    p_exp.set_defaults(func=_cmd_explain)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Console-script entry point."""
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
