"""Prompt templates for generate / refactor / explain tasks.

Each template starts with a machine-readable ``TASK_TYPE:`` line. The
offline :class:`~code_assistant.llm.TemplateLLM` uses that line to route
deterministically; a real LLM simply reads it as an instruction.
"""

from __future__ import annotations

_RULES = (
    "Rules: output Python code only (for generate/refactor); use only the "
    "standard library; include a docstring; never use eval, exec, os.system, "
    "or shell commands; keep the code self-contained."
)


def build_generate_prompt(task: str, context: str = "") -> str:
    """Prompt asking for a new function that satisfies ``task``."""
    return (
        "TASK_TYPE: generate\n"
        f"Task: {task}\n"
        f"{context}\n"
        f"{_RULES}\n"
        "Write the function now."
    )


def build_refactor_prompt(code: str, instruction: str, context: str = "") -> str:
    """Prompt asking for ``code`` refactored according to ``instruction``."""
    return (
        "TASK_TYPE: refactor\n"
        f"Instruction: {instruction}\n"
        f"{context}\n"
        "Original code:\n```python\n"
        f"{code}\n```\n"
        f"{_RULES}\n"
        "Write the refactored code now."
    )


def build_explain_prompt(code: str, context: str = "") -> str:
    """Prompt asking for a plain-English explanation of ``code``."""
    return (
        "TASK_TYPE: explain\n"
        f"{context}\n"
        "Explain what this code does, in plain English, in 2-4 sentences:\n"
        "```python\n"
        f"{code}\n```"
    )
