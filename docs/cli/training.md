# Training Commands

The `buddy train` group (`buddy.cli.simple_train_cli`) wraps the
[`buddy.train`](../training/overview.md) API for one-line local fine-tuning. It
is available when the training dependencies are installed:

```bash
pip install "buddy-ai[training]"
```

## Commands

| Command | Description |
|---------|-------------|
| `buddy train <data> --name <name>` | Train a model on a file or directory |
| `buddy train test <name>` | Generate a sample from a trained model |
| `buddy train list` | List your trained models |
| `buddy train delete <name>` | Delete a trained model |
| `buddy train models` | List available open-source base models |
| `buddy train install-deps` | Install the training dependencies |

## Train

```bash
buddy train /path/to/data --name my-model
buddy train /path/to/data --name coder --model phi-2 --epochs 5
```

| Option | Alias | Description |
|--------|-------|-------------|
| `--name` | `-n` | **Required.** Name for the trained model |
| `--model` | `-m` | Base model alias or full Hugging Face id |
| `--epochs` | `-e` | Training epochs (default 3) |
| `--description` | `-d` | Description stored in metadata |
| `--force` | `-f` | Overwrite an existing model |

The data path is a positional argument and must exist. Models are saved under
`~/.buddy/trained_models/<name>` (see [Model Training](../training/training.md)).

## Test

```bash
buddy train test my-model --prompt "Hello, how are you?"
buddy train test my-model -l 150
```

| Option | Alias | Description |
|--------|-------|-------------|
| `--prompt` | `-p` | Prompt to send (a default is used if omitted) |
| `--max-length` | `-l` | Number of tokens to generate (default 100) |

## List and delete

```bash
buddy train list
buddy train delete old-model        # prompts for confirmation
buddy train delete old-model --yes  # skip the prompt
```

`delete` accepts `-y`/`--yes` to skip confirmation.

## Available base models

```bash
buddy train models
```

Prints the curated list of open-source base models and their aliases (e.g.
`distilgpt2`, `phi-2`, `mistral-7b`, `llama3-8b`). Gated models such as Llama,
Mistral, and Gemma require a Hugging Face login first.

## Install dependencies

```bash
buddy train install-deps
```

Installs `transformers`, `torch`, `datasets`, and `accelerate` via pip — an
alternative to the `[training]` extra.

## See also

- [Training Overview](../training/overview.md)
- [Data Preparation](../training/data-prep.md) · [Model Training](../training/training.md)
