"""Convert instruction/code pairs into trainer-ready JSONL (stdlib only).

Input (JSON): a list of objects with ``instruction``, optional ``context``,
and ``code`` — e.g. exported from merged pull requests.
Output (JSONL): one ``{"prompt": ..., "completion": ...}`` object per line,
with the prompt shaped exactly like the runtime generate prompt, so the
model trains on the distribution it will see at inference time.

Usage:
    python3 training/prepare_dataset.py --input pairs.json --output out.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def convert_pair(pair: dict) -> dict:
    """Convert one raw pair dict into a ``prompt``/``completion`` record."""
    instruction = str(pair.get("instruction", "")).strip()
    if not instruction:
        raise ValueError("pair is missing a non-empty 'instruction'")
    code = str(pair.get("code", "")).strip()
    if not code:
        raise ValueError("pair is missing a non-empty 'code'")
    context = str(pair.get("context", "")).strip()
    prompt = "TASK_TYPE: generate\n"
    if context:
        prompt += f"{context}\n"
    prompt += f"Task: {instruction}\nWrite the function now."
    return {"prompt": prompt, "completion": code}


def convert_file(input_path: str | Path, output_path: str | Path) -> int:
    """Convert a JSON list file to JSONL; returns the number of records."""
    raw = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("input JSON must be a list of pair objects")
    records = [convert_pair(pair) for pair in raw]
    with Path(output_path).open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")
    return len(records)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Input JSON list file")
    parser.add_argument("--output", required=True, help="Output JSONL file")
    args = parser.parse_args(argv)
    count = convert_file(args.input, args.output)
    print(f"Wrote {count} record(s) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
