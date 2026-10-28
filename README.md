# Code Generation / Refactoring Assistant

> An AI tool specialised for a **Python codebase**: it indexes the code you
> actually have, retrieves the symbols relevant to a natural-language task,
> generates or refactors code with an LLM, and then — before trusting a
> single line — **validates it with AST guardrails and proves it with an
> automated test harness.**

Built by **Rajesh Kodaganti** — AI Software Engineer.
Core package: **Python standard library only.** No API keys needed to run
the demo, the CLI, or the tests (a deterministic offline LLM is included).

---

## What it does

- **Generate** a function from a natural-language task, grounded in your
  codebase's real symbols (not hallucinated APIs).
- **Refactor** existing code (offline demo refactor: safe, mechanical
  docstring insertion — the pattern a real LLM backend plugs into).
- **Explain** code in plain English.
- **Guardrail everything:** syntax check, AST scan for dangerous patterns,
  and a subprocess test harness with a timeout — generated code is
  untrusted until it passes all three.

## Architecture

```
                        ┌────────────────────┐
   natural-language     │      indexer.py     │   ast parsing: modules,
   task / file  ───────▶│  codebase indexing  │──▶ classes, functions,
                        └─────────┬──────────┘    signatures, docstrings
                                  │               + local dependency graph
                                  ▼
                        ┌────────────────────┐
                        │      context.py     │   keyword retrieval,
                        │  context retrieval  │──▶ ranked symbols that fit
                        │  + token budget     │    a strict token budget
                        └─────────┬──────────┘
                                  ▼
                        ┌────────────────────┐      ┌──────────────────┐
                        │     prompts.py      │─────▶│       llm.py      │
                        │  generate / refactor│      │ streaming LLM     │
                        │  / explain templates│      │ protocol:         │
                        └────────────────────┘      │ TemplateLLM       │
                                                    │ (offline) / OpenAI│
                                                    └────────┬─────────┘
                                                             ▼
                        ┌────────────────────┐      ┌──────────────────┐
                        │     harness.py      │◀─────│    validator.py   │
                        │  subprocess unittest│      │ AST guardrails:   │
                        │  + timeout, isolated│      │ no eval / shell / │
                        └────────────────────┘      │ deletion / dunder │
                              pass / fail           └──────────────────┘
```

## The 4 key engineering challenges — and how each is addressed

### 1. Context Window Management — `indexer.py` + `context.py`
A repository never fits in a prompt. The indexer parses every module with
`ast` and builds a **dependency graph** of local imports. The context
builder scores every symbol against the task (name matches weigh most,
then signature, then docstring), ranks them, and assembles a block that
fits a **strict token budget** (simple ~4-chars/token estimator) —
most-relevant first, so the budget never drops the symbol that matters.
Reverse lookups (`dependents_of`) answer "what breaks if I change this?"

### 2. Safety & Correctness — `validator.py`
Generated code is treated as untrusted. Before anything else runs it:
`compile()` for syntax, then an AST scan rejecting `eval`/`exec`/
`__import__`, `os.system`/`os.popen`, `subprocess` with `shell=True`,
file deletion (`os.remove`, `shutil.rmtree`, …), and dunder attribute
access (`x.__class__` — a classic sandbox-escape vector). Missing
docstrings are non-fatal style warnings.

### 3. Testing Harness — `harness.py`
Validation says code is *plausible*; the harness says it is *right*.
Generated code and a `unittest` snippet are written to a fresh temp
directory and executed with `python -m unittest` in a **subprocess with a
timeout** — never in-process — returning pass/fail with full output.

### 4. Streaming & Latency — `llm.py`
Every backend implements the same `LLM` protocol with two faces:
`generate()` (whole string) and `stream()` (an **iterator of chunks**).
Interactive tools stream so users see code as it is produced and can
abort early instead of waiting on a full completion. The offline
`TemplateLLM` streams line-by-line; the `OpenAILLM` stub streams API
deltas through the identical interface — backends are interchangeable.

## Quickstart

```bash
# No dependencies to install — stdlib only. Python 3.10+.
python3 examples/run_demo.py

# Run the test suite (27 tests)
python3 -m unittest discover -s tests -v

# Optional: install the CLI entry point
pip install -e .
code-assistant index examples/sample_codebase
```

## CLI usage

```bash
# What is in this codebase, and how do the modules depend on each other?
code-assistant index examples/sample_codebase

# Generate, grounded in retrieved context, streamed chunk by chunk
code-assistant generate "Write a function \`add(a, b)\` that returns the sum" \
    --codebase examples/sample_codebase --stream

# Refactor a file (offline LLM applies a safe mechanical refactor)
code-assistant refactor path/to/file.py "add missing docstrings"

# Explain a file
code-assistant explain path/to/file.py
```

Without installing, run it from `src/`:
`PYTHONPATH=src python3 -m code_assistant.cli index examples/sample_codebase`
— or just use `examples/run_demo.py`, which wires the pipeline end to end:
index → context (400-token budget) → streamed generation → validation →
harness, against the bundled sample package.

## Project structure

```
codegen-refactor-assistant/
├── README.md                  # this file
├── pyproject.toml             # package: code_assistant, CLI entry point
├── requirements.txt           # stdlib-only note + optional extras
├── LICENSE                    # MIT
├── src/code_assistant/
│   ├── __init__.py            # public API re-exports
│   ├── indexer.py             # ast indexing + dependency graph
│   ├── context.py             # retrieval + token-budget assembly
│   ├── prompts.py             # generate / refactor / explain templates
│   ├── llm.py                 # streaming LLM protocol, TemplateLLM, OpenAI stub
│   ├── validator.py           # AST safety guardrails + style warnings
│   ├── harness.py             # isolated subprocess test harness
│   └── cli.py                 # argparse CLI (index/generate/refactor/explain)
├── examples/
│   ├── sample_codebase/sample_pkg/   # calculator, text_utils, inventory
│   └── run_demo.py            # full end-to-end pipeline, offline
├── training/                  # LoRA/QLoRA fine-tuning path (see below)
│   ├── README.md
│   ├── lora_config.yaml
│   ├── prepare_dataset.py     # pairs → JSONL (stdlib only)
│   └── finetune_lora.py       # lazy torch/peft imports; GPU + extras only
└── tests/                     # unittest: indexer, context, validator,
                               # harness, TemplateLLM (27 tests)
```

## Fine-tuning path (LoRA / QLoRA) — `training/`

Retrieval does most of the domain work, but a base model can be made
genuinely codebase-native with **LoRA adapters** trained on (task +
retrieved context → accepted code) pairs mined from merged PRs. Adapters
are small, swappable per codebase, and cheap to retrain as code evolves.
QLoRA (4-bit base + adapters on the attention projections) fits a 7B-class
code model on a single GPU. The training code is **fully separated** from
the core: `prepare_dataset.py` is stdlib-only, and `finetune_lora.py`
lazy-imports `torch`/`peft` and is never required to run or test the
assistant. Every fine-tuned checkpoint should still be gated through this
project's validator + harness on held-out tasks before it is trusted.
See [`training/README.md`](training/README.md).

## Roadmap

- [ ] Embedding-based retrieval alongside keyword scoring (hybrid search)
- [ ] Cross-encoder re-ranking of retrieved symbols
- [ ] Response/chunk caching for repeated tasks
- [ ] Multi-file edits with dependency-graph-aware change planning
- [ ] Evaluation suite: retrieval precision vs. harness pass-rate per model
- [ ] Editor integration (LSP / VS Code) over the streaming interface

## License

MIT — see [LICENSE](LICENSE). © 2026 Rajesh Kodaganti.
