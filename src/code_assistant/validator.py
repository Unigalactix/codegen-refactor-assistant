"""Safety & correctness guardrails for generated code.

Generated code is *untrusted* until it clears this module. Checks, in
order:

1. **Syntax** — ``compile()`` must succeed.
2. **Dangerous patterns (AST scan)** — calls to ``eval`` / ``exec`` /
   ``__import__``, ``os.system`` / ``os.popen``, any ``subprocess`` call
   with ``shell=True``, file deletion (``os.remove``, ``os.unlink``,
   ``shutil.rmtree``, …), and dunder attribute access (``x.__class__`` …),
   a classic sandbox-escape vector.
3. **Style warnings (non-fatal)** — e.g. functions without docstrings.

Only code with no errors should ever reach the test harness — and even
then, the harness runs it in a subprocess with a timeout.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

_BANNED_CALLS = {"eval", "exec", "__import__"}
_BANNED_ATTRS: dict[str, set[str]] = {
    "os": {"system", "popen", "remove", "unlink", "rmdir", "removedirs"},
    "shutil": {"rmtree"},
    "pathlib": {"unlink"},
}
_SUBPROCESS_FUNCS = {"call", "run", "Popen", "check_call", "check_output"}


@dataclass
class ValidationResult:
    """Outcome of validating a code snippet."""

    syntax_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True when the code compiles and has no safety errors."""
        return self.syntax_valid and not self.errors

    @property
    def passed(self) -> bool:
        """Alias for :attr:`is_valid`."""
        return self.is_valid


def _dotted(node: ast.expr) -> str:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _scan(tree: ast.Module, result: ValidationResult) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _BANNED_CALLS:
                result.errors.append(f"line {node.lineno}: banned call '{func.id}()'")
            if isinstance(func, ast.Attribute):
                dotted = _dotted(func)
                root, _, attr = dotted.partition(".")
                if root in _BANNED_ATTRS and attr.split(".")[0] in _BANNED_ATTRS[root]:
                    result.errors.append(f"line {node.lineno}: banned call '{dotted}()'")
                if root == "subprocess" and attr in _SUBPROCESS_FUNCS:
                    shell = any(
                        kw.arg == "shell" and isinstance(kw.value, ast.Constant)
                        and kw.value.value is True
                        for kw in node.keywords
                    )
                    if shell:
                        result.errors.append(
                            f"line {node.lineno}: subprocess with shell=True is banned"
                        )
        if isinstance(node, ast.Attribute) and node.attr.startswith("__") \
                and node.attr.endswith("__"):
            result.errors.append(
                f"line {getattr(node, 'lineno', 0)}: dunder access '{node.attr}' is banned"
            )
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if ast.get_docstring(node) is None:
                result.warnings.append(
                    f"line {node.lineno}: function '{node.name}' is missing a docstring"
                )


def validate_code(code: str) -> ValidationResult:
    """Validate ``code`` for syntax, safety, and basic style.

    Args:
        code: Python source to check.

    Returns:
        A :class:`ValidationResult`; ``is_valid`` is the gate callers use.
    """
    try:
        compile(code, "<generated>", "exec")
    except SyntaxError as exc:
        return ValidationResult(
            syntax_valid=False,
            errors=[f"SyntaxError: {exc.msg} (line {exc.lineno})"],
        )
    result = ValidationResult(syntax_valid=True)
    _scan(ast.parse(code), result)
    return result
