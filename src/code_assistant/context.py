"""Context-window management: retrieval + budget-aware assembly.

A real codebase never fits in an LLM's context window. This module scores
every indexed symbol against the natural-language task (keyword overlap
over names, signatures, and docstrings), ranks them, and assembles a
context block that fits a strict token budget — most-relevant first, so
truncation always drops the *least* relevant material.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .indexer import CodebaseIndex, Symbol

_STOPWORDS = {
    "a", "an", "the", "to", "of", "for", "that", "with", "and", "or",
    "in", "on", "is", "it", "write", "create", "function", "code",
    "new", "make", "implement", "returns", "return", "given", "using",
}


def estimate_tokens(text: str) -> int:
    """Cheap token estimate (~4 characters per token for English/code)."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def tokenize(text: str) -> list[str]:
    """Split text (incl. snake_case / camelCase identifiers) into keywords."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    words = re.findall(r"[a-z0-9]+", spaced.lower().replace("_", " "))
    return [w for w in words if w not in _STOPWORDS and len(w) > 1]


@dataclass
class ScoredSymbol:
    """A symbol with its relevance score for a task."""

    symbol: Symbol
    score: float


@dataclass
class ContextBlock:
    """The assembled, budget-fitting context for a prompt."""

    text: str
    symbols: list[Symbol] = field(default_factory=list)
    token_count: int = 0
    token_budget: int = 0


def score_symbol(symbol: Symbol, keywords: list[str]) -> float:
    """Score a symbol: name matches weigh most, then signature, then docs."""
    name_words = set(tokenize(symbol.name)) | set(tokenize(symbol.qualname))
    sig_words = set(tokenize(symbol.signature))
    doc_words = set(tokenize(symbol.docstring))
    score = 0.0
    for kw in keywords:
        if kw in name_words:
            score += 3.0
        if kw in sig_words:
            score += 1.5
        if kw in doc_words:
            score += 1.0
    return score


def rank_symbols(index: CodebaseIndex, task: str) -> list[ScoredSymbol]:
    """Rank all indexed symbols by relevance to ``task``, best first."""
    keywords = tokenize(task)
    scored = [ScoredSymbol(s, score_symbol(s, keywords)) for s in index.symbols]
    scored.sort(key=lambda item: (-item.score, item.symbol.qualname))
    return scored


def build_context(
    index: CodebaseIndex, task: str, token_budget: int = 1200, top_k: int = 8
) -> ContextBlock:
    """Assemble a context block for ``task`` within ``token_budget``.

    Symbols are added most-relevant first; a symbol that would breach the
    budget is skipped (a smaller, less relevant one may still fit).
    Zero-score symbols are never included.
    """
    header = f"# Relevant codebase context for task: {task}\n"
    block = ContextBlock(text=header, token_budget=token_budget,
                         token_count=estimate_tokens(header))
    for scored in rank_symbols(index, task)[:top_k]:
        if scored.score <= 0:
            break
        chunk = scored.symbol.describe() + "\n"
        cost = estimate_tokens(chunk)
        if block.token_count + cost > token_budget:
            continue
        block.text += chunk
        block.symbols.append(scored.symbol)
        block.token_count += cost
    return block
