"""LoRA / QLoRA fine-tuning — REQUIRES GPU + OPTIONAL EXTRAS.

This script is deliberately *not* part of the core package:

* ``torch`` / ``peft`` / ``transformers`` are imported lazily inside
  :func:`main`, so importing this module (or running the core, demo, or
  tests) never requires them.
* Install extras first:  ``pip install -e ".[train]"``
* Prepare data first:    ``python3 training/prepare_dataset.py ...``
* Config:                ``training/lora_config.yaml``

What it does, in outline: load the base code model in 4-bit (QLoRA),
attach LoRA adapters to the attention projections, train on the JSONL
from ``prepare_dataset.py``, and save only the adapter — a few tens of MB
that can be swapped per codebase on top of one shared base model.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _read_simple_config(path: str | Path) -> dict[str, str]:
    """Read the flat ``key: value`` lines of lora_config.yaml (no PyYAML)."""
    config: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" in line:
            key, _, value = line.partition(":")
            config[key.strip()] = value.strip().strip('"')
    return config


def main(argv: list[str] | None = None) -> int:
    """Run QLoRA fine-tuning. Raises a clear error without the extras."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="training/lora_config.yaml")
    args = parser.parse_args(argv)

    try:
        import torch  # noqa: F401
        from datasets import Dataset  # noqa: F401
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training  # noqa: F401
        from transformers import (  # noqa: F401
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:
        raise SystemExit(
            "Fine-tuning requires a GPU machine with the training extras:\n"
            '    pip install -e ".[train]"\n'
            f"(missing: {exc.name}) — the core assistant does NOT need these."
        ) from exc

    config = _read_simple_config(args.config)
    dataset_path = config.get("dataset", "training/data/train.jsonl")
    records = [json.loads(line) for line in
               Path(dataset_path).read_text(encoding="utf-8").splitlines() if line]
    if not records:
        raise SystemExit(f"No training records in {dataset_path}; "
                         "run prepare_dataset.py first.")

    # --- Sketch of the real run (executed only with extras + GPU) -------
    # bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4")
    # model = AutoModelForCausalLM.from_pretrained(
    #     config["base_model"], quantization_config=bnb, device_map="auto")
    # model = prepare_model_for_kbit_training(model)
    # lora = LoraConfig(r=int(config["lora_r"]),
    #                   lora_alpha=int(config["lora_alpha"]),
    #                   target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    #                   task_type="CAUSAL_LM")
    # model = get_peft_model(model, lora)
    # ... tokenise prompt+completion, Trainer(...).train(), then
    # model.save_pretrained(config["output_dir"])  # adapter only
    raise SystemExit(
        "Training extras are installed, but this portfolio sketch stops "
        "before the GPU run — wire the commented Trainer block to your "
        "machine, dataset, and base model. "
        f"Config loaded OK ({len(config)} keys), dataset records: {len(records)}."
    )


if __name__ == "__main__":
    raise SystemExit(main())
