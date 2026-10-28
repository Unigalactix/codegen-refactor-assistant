# Fine-Tuning Path: LoRA / QLoRA

The core assistant works with any LLM behind the `LLM` protocol — no
fine-tuning is required to run it. Fine-tuning is how you make a *base*
model genuinely **domain-specific**: aligned to one codebase's naming,
idioms, helper APIs, and review standards, so generated code calls the
project's own functions instead of inventing plausible-looking ones.

## Approach

| Piece | Choice | Why |
|---|---|---|
| Method | **LoRA** (QLoRA for large models) | Trains <1% of weights; adapters are small, swappable per-codebase, and cheap to retrain as the code evolves |
| Base model | A code model (e.g. a 7B-class coder model) | Small enough for a single GPU with QLoRA 4-bit loading |
| Data | Instruction / code pairs mined from the repo: (task, retrieved context) → accepted code | Mirrors exactly how the assistant prompts at inference time |
| Targets | `q_proj, k_proj, v_proj, o_proj` (see `lora_config.yaml`) | Attention projections give the best quality / parameter trade-off |
| Safety loop | Every checkpoint is scored through `validator.py` + `harness.py` on a held-out task set | A fine-tune that writes more dangerous or failing code is rejected, however fluent it looks |

## Pipeline

1. **Prepare data** (stdlib only, runs anywhere):

   ```bash
   python3 training/prepare_dataset.py --input pairs.json --output training/data/train.jsonl
   ```

   Input: a JSON list of `{"instruction": ..., "context": ..., "code": ...}`
   objects (e.g. exported from merged PRs: description + diff context →
   final code). Output: JSONL in the chat/instruction format the trainer
   consumes.

2. **Fine-tune** (GPU + optional extras required — *not* part of the core):

   ```bash
   pip install -e ".[train]"     # torch, peft, transformers, datasets, accelerate
   python3 training/finetune_lora.py --config training/lora_config.yaml
   ```

   `finetune_lora.py` lazy-imports `torch` / `peft` inside `main()`, so
   importing or reading the file never breaks the stdlib-only core.

3. **Serve the adapter**: load base model + adapter behind the `LLM`
   protocol (same streaming interface as `TemplateLLM` / `OpenAILLM`),
   then let the existing validator and harness gate its output.

## Honest limits

- LoRA teaches style and local API usage; it does not teach reasoning the
  base model lacks. Retrieval (the indexer + context builder) still does
  most of the domain work.
- QLoRA's 4-bit quantisation trades a little quality for a lot of memory;
  evaluate per-checkpoint rather than assuming.
- Dataset quality dominates: merged, reviewed code only — never raw
  unreviewed generations, or the model learns its own mistakes.
