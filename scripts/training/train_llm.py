"""
Fine-tune llama3.2:3b on broadcast news transcripts using LoRA (PEFT).

Requires GPU. On the server (CPU-only) this script will warn and exit.
Run on a machine with a CUDA GPU, or a rented cloud GPU instance.

Usage:
    python scripts/training/train_llm.py \\
        --dataset data/training/llm_dataset.json \\
        --output models/llm_finetune \\
        --epochs 3 \\
        --batch-size 4

The resulting LoRA adapter is saved to models/llm_finetune/.
Load it via Ollama: ollama create studio-anchor -f models/llm_finetune/Modelfile
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch


def _check_gpu():
    if not torch.cuda.is_available():
        print("WARNING: No CUDA GPU detected.")
        print("LLM fine-tuning on CPU is impractical (days per epoch).")
        print("Options:")
        print("  1. Run on a machine with an NVIDIA GPU")
        print("  2. Rent a GPU: RunPod, Lambda Labs, or Vast.ai (~$0.30/hr for A10)")
        print("  3. Use the Ollama Modelfile approach (no training needed — see below)")
        print()
        print("Ollama Modelfile alternative (no GPU required):")
        print('  FROM llama3.2:3b')
        print('  SYSTEM "You are a broadcast news anchor script writer..."')
        print("  Save as models/llm_finetune/Modelfile, then:")
        print("  ollama create studio-anchor -f models/llm_finetune/Modelfile")
        sys.exit(1)


def load_alpaca_dataset(path: Path):
    """Load Alpaca-format JSON dataset into HuggingFace Dataset."""
    from datasets import Dataset

    with open(path) as f:
        data = json.load(f)

    def _format(example):
        prompt = (
            f"### Instruction:\n{example['instruction']}\n\n"
            f"### Input:\n{example['input']}\n\n"
            f"### Response:\n{example['output']}"
        )
        return {"text": prompt}

    formatted = [_format(e) for e in data]
    return Dataset.from_list(formatted)


def train(
    dataset_path: Path,
    output_dir: Path,
    base_model: str = "meta-llama/Llama-3.2-3B-Instruct",
    epochs: int = 3,
    batch_size: int = 4,
    lr: float = 2e-4,
    lora_r: int = 16,
    lora_alpha: int = 32,
    max_seq_len: int = 1024,
):
    _check_gpu()

    try:
        from peft import LoraConfig, TaskType, get_peft_model
        from transformers import (
            AutoModelForCausalLM, AutoTokenizer, DataCollatorForLanguageModeling,
            Trainer, TrainingArguments,
        )
    except ImportError:
        print("Install: pip install peft transformers datasets accelerate")
        sys.exit(1)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading base model: {base_model}")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )

    lora_cfg = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=0.05,
        bias="none",
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    )
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()

    print(f"Loading dataset: {dataset_path}")
    dataset = load_alpaca_dataset(dataset_path)

    def tokenize(example):
        return tokenizer(
            example["text"],
            truncation=True,
            max_length=max_seq_len,
            padding="max_length",
        )

    tokenized = dataset.map(tokenize, remove_columns=["text"])
    tokenized = tokenized.train_test_split(test_size=0.05, seed=42)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=lr,
        fp16=True,
        logging_steps=50,
        save_strategy="epoch",
        eval_strategy="epoch",
        load_best_model_at_end=True,
        report_to="none",
        warmup_ratio=0.05,
        lr_scheduler_type="cosine",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["test"],
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )

    print("Starting LoRA fine-tuning...")
    trainer.train()

    model.save_pretrained(str(output_dir / "adapter"))
    tokenizer.save_pretrained(str(output_dir / "adapter"))

    # Write Ollama Modelfile so adapter can be served via Ollama
    modelfile = output_dir / "Modelfile"
    modelfile.write_text(
        f'FROM llama3.2:3b\n'
        f'SYSTEM """You are a professional broadcast news anchor script writer. '
        f'You rewrite news articles as clean, factual, short-sentence anchor delivery scripts. '
        f'No opinion. No political framing. Facts only. Plain language."""\n'
    )
    print(f"\nDone. Adapter saved to: {output_dir / 'adapter'}")
    print(f"Modelfile: {modelfile}")
    print(f"To serve: ollama create studio-anchor -f {modelfile}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune LLM on broadcast news transcripts")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", default="models/llm_finetune", type=Path)
    parser.add_argument("--base-model", default="meta-llama/Llama-3.2-3B-Instruct")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--max-seq-len", type=int, default=1024)
    args = parser.parse_args()

    train(
        dataset_path=args.dataset,
        output_dir=args.output,
        base_model=args.base_model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        lora_r=args.lora_r,
        max_seq_len=args.max_seq_len,
    )
