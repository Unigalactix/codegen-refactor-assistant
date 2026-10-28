"""Automated test harness: generated code is only trusted if tests pass.

Writes the generated code to ``solution.py`` and the caller's test snippet
to ``test_solution.py`` inside a fresh temporary directory, then runs the
tests with :mod:`subprocess` (``python -m unittest``) under a timeout.
The generated code never runs in this process — isolation by construction.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class HarnessResult:
    """Outcome of running tests against generated code."""

    passed: bool
    returncode: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False

    @property
    def output(self) -> str:
        """Combined stdout + stderr, for display / logging."""
        return (self.stdout + self.stderr).strip()

    @property
    def success(self) -> bool:
        """Alias for :attr:`passed`."""
        return self.passed


def run_generated_code(
    code: str, test_code: str, timeout: int = 10
) -> HarnessResult:
    """Run ``test_code`` (unittest) against ``code`` in isolation.

    Args:
        code: Generated Python source, written to ``solution.py``. Tests
            import it as ``from solution import ...``.
        test_code: A ``unittest`` test module source.
        timeout: Seconds before the run is killed and reported as failed.

    Returns:
        A :class:`HarnessResult` with pass/fail, exit code, and output.
    """
    with tempfile.TemporaryDirectory(prefix="code-assistant-harness-") as tmp:
        workdir = Path(tmp)
        (workdir / "solution.py").write_text(code, encoding="utf-8")
        (workdir / "test_solution.py").write_text(test_code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "unittest", "-v", "test_solution"],
                cwd=tmp, capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            return HarnessResult(
                passed=False, returncode=-1,
                stdout=(exc.stdout or b"").decode() if isinstance(exc.stdout, bytes)
                else (exc.stdout or ""),
                stderr=f"Timed out after {timeout}s", timed_out=True,
            )
        return HarnessResult(
            passed=proc.returncode == 0,
            returncode=proc.returncode,
            stdout=proc.stdout, stderr=proc.stderr,
        )
