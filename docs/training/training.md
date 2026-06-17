# Model Training

`train_model` runs the whole pipeline — process, fine-tune, save — in a single
call.

## `train_model`

```python
from buddy.train import train_model

path = train_model(
    data_path="/path/to/data",   # file or directory of training text
    name="my-model",             # saved under ~/.buddy/trained_models/my-model
    model="phi-2",               # base model alias or HF id (optional)
    epochs=3,                    # optional, default 3
    description="My custom bot", # optional, stored in metadata
    force=False,                 # set True to overwrite an existing model
)
print(path)  # absolute path to the saved model directory
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data_path` | `str` | — | Path to a file or directory of training data |
| `name` | `str` | — | Name for the trained model |
| `model` | `str` | `microsoft/DialoGPT-small` | Base model alias or full Hugging Face id |
| `epochs` | `int` | `3` | Number of training epochs |
| `description` | `str` | `Model trained on <data_path>` | Free-text description saved in metadata |
| `force` | `bool` | `False` | Overwrite if a model with this name exists |

It returns the **path** to the saved model directory. If the model already
exists and `force=False`, training is skipped and the existing path is returned.

!!! info "Fixed, sensible defaults"
    Batch size (4), learning rate (5e-5), and max sequence length (512) are
    hard-coded. Training automatically uses CUDA (with fp16) when a GPU is
    available, otherwise CPU. A 90/10 train/eval split is created
    automatically, with early stopping on `eval_loss`.

## Choosing a base model

Pass either a **full Hugging Face id** (e.g. `"microsoft/phi-2"`) or one of the
built-in aliases. See the whole list with:

```python
from buddy.train import list_available_models
list_available_models()
```

A few of the available aliases:

| Alias | Hugging Face id | Notes |
|-------|-----------------|-------|
| `distilgpt2` | `distilgpt2` | Tiny, fast, no auth |
| `dialogpt-small` | `microsoft/DialoGPT-small` | **Default** base |
| `phi-2` | `microsoft/phi-2` | No auth |
| `gpt-neo-125m` | `EleutherAI/gpt-neo-125M` | No auth |
| `mistral-7b` | `mistralai/Mistral-7B-v0.1` | Requires HF auth |
| `llama3-8b` | `meta-llama/Meta-Llama-3-8B` | Requires HF auth |

!!! warning "Gated models need Hugging Face auth"
    Llama, Mistral, and Gemma aliases download from gated repos. Run
    `huggingface-cli login` (and accept the model's license on the Hub) first.
    Beginner-friendly, ungated picks: `distilgpt2`, `phi-2`, `gpt-neo-125m`.

## What gets saved

After training, `~/.buddy/trained_models/<name>/` contains the model weights and
tokenizer plus:

- `metadata.json` — name, description, base model, epochs, data path, file/char
  counts, and creation timestamp
- `training_info.json` and `training_report.json` — device, duration, final
  loss, sample counts, and the full config

## Using a trained model as an Agent

The easiest path is `use_with_agent`, which loads your model and returns a ready
[Agent](../core/agents.md):

```python
from buddy.train import use_with_agent

agent = use_with_agent("my-model", agent_name="My Custom Agent")
response = agent.run("Hello, how can you help me?")
print(response.content)
```

For more control, build the model wrapper yourself with `create_trained_model`
and pass it as any other model:

```python
from buddy import Agent
from buddy.train import create_trained_model

model = create_trained_model(
    model_path="~/.buddy/trained_models/my-model",
    temperature=0.8,
    max_length=300,
)
agent = Agent(name="My Agent", model=model)
```

`create_trained_model` returns a `BuddyTrainedModel`, which accepts generation
parameters such as `temperature`, `top_p`, `top_k`, `repetition_penalty`,
`max_length`, and `do_sample`.

!!! note "Local models are text-only"
    `BuddyTrainedModel` runs synchronously and does **not** support tool calls,
    structured output, or streaming — those arguments are accepted but ignored.

## Next steps

- [Evaluating Trained Models](evaluation.md)
- [CLI: Training Commands](../cli/training.md)
