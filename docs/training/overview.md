# Training Overview

`buddy.train` is a **one-line local fine-tuning** toolkit. Point it at a folder
of files, give your model a name, and it processes the data, fine-tunes an
open-source base model on your machine, and saves the result — no hosted
service, no API keys.

!!! note "What it is — and isn't"
    `buddy.train` is a thin, opinionated wrapper around **Hugging Face
    Transformers** (and PEFT). It runs **entirely locally** with sensible,
    hard-coded defaults so you don't have to think about hyperparameters. It is
    designed for **small, personal models** (the default base is
    `microsoft/DialoGPT-small`). It is **not** a distributed-training platform,
    and it does not call out to any cloud training service.

## Installation

Training pulls in heavy ML dependencies, so they live in the optional
`[training]` extra:

```bash
pip install "buddy-ai[training]"
```

This installs `torch`, `transformers`, `datasets`, `accelerate`, and `peft`.
You can also install them from inside the CLI:

```bash
buddy train install-deps
```

## The simple API

Three functions cover the common workflow:

```python
from buddy.train import train_model, test_model, list_models

# 1. Train a model on a folder of files
train_model("/path/to/data", "my-model")

# 2. Test it with a prompt
test_model("my-model", "Hello, how are you?")

# 3. List everything you've trained
list_models()
```

The package also exports `delete_model`, `use_with_agent`, and the lower-level
building blocks `DataProcessor`, `ModelTrainer`, `ModelManager`,
`BuddyTrainedModel`, and `create_trained_model` for power users.

## Or use the CLI

```bash
buddy train /path/to/data --name my-model
buddy train test my-model --prompt "Hello!"
buddy train list
```

See [CLI: Training Commands](../cli/training.md) for every flag.

## How it works

| Stage | Component | What happens |
|-------|-----------|--------------|
| **Process** | `DataProcessor` | Recursively reads every file, detects encoding, extracts text (incl. PDF/DOCX), cleans and chunks it |
| **Train** | `ModelTrainer` | Loads the base model, tokenizes, runs causal-LM fine-tuning with HF `Trainer` |
| **Save** | `train_model` | Writes the model, tokenizer, and metadata under `~/.buddy/trained_models/<name>` |
| **Use** | `use_with_agent` / `BuddyTrainedModel` | Wraps the saved model as a Buddy [Agent](../core/agents.md) backend |

## Where models live

Every trained model is saved to:

```text
~/.buddy/trained_models/<model-name>/
```

This directory holds the model weights, tokenizer, and a `metadata.json`
describing how it was trained.

## Next steps

- [Data Preparation](data-prep.md) — what `DataProcessor` accepts
- [Model Training](training.md) — parameters, base models, and using your model
- [Evaluating Trained Models](evaluation.md) — testing and benchmarking
