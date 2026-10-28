"""Domain-specific code generation / refactoring assistant for Python.

Core pipeline: index a codebase (:mod:`.indexer`) → retrieve the context
that fits the window (:mod:`.context`) → prompt an LLM (:mod:`.prompts`,
:mod:`.llm`) → guardrail the output (:mod:`.validator`) → prove it with
tests (:mod:`.harness`). Standard library only.
"""

from .context import ContextBlock, build_context, estimate_tokens
from .harness import HarnessResult, run_generated_code
from .indexer import CodebaseIndex, ModuleInfo, Symbol, index_codebase
from .llm import LLM, OpenAILLM, TemplateLLM
from .validator import ValidationResult, validate_code

__version__ = "0.1.0"

__all__ = [
    "CodebaseIndex",
    "ContextBlock",
    "HarnessResult",
    "LLM",
    "ModuleInfo",
    "OpenAILLM",
    "Symbol",
    "TemplateLLM",
    "ValidationResult",
    "__version__",
    "build_context",
    "estimate_tokens",
    "index_codebase",
    "run_generated_code",
    "validate_code",
]
