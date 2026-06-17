# Evaluating Trained Models

`buddy.train` focuses on training and quick, qualitative checks rather than a
formal metrics suite. This page covers what the package actually measures.

!!! note "Scope"
    There is **no built-in perplexity, BLEU, or accuracy grader** in
    `buddy.train`. Evaluation here means: a held-out **`eval_loss`** during
    training, plus utilities to **generate samples** and measure **throughput**.
    For structured, prompt-level grading of agents, use the
    [Evaluation System](../advanced/evaluation.md).

## Quick test with `test_model`

The fastest check is to prompt the model and read the output:

```python
from buddy.train import test_model

response = test_model("my-model", "Hello, how are you?", max_length=100)
print(response)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | — | Name of a model under `~/.buddy/trained_models` |
| `prompt` | `str` | `Hello, how can I help you today?` | Prompt to send |
| `max_length` | `int` | `100` | Number of new tokens to generate |

Or from the CLI:

```bash
buddy train test my-model --prompt "Hello, how are you?"
```

## Training loss

During fine-tuning, the data is split 90/10 and the Hugging Face `Trainer`
tracks **`eval_loss`** on the held-out split, keeping the best checkpoint
(`load_best_model_at_end`) with early stopping. The final values are written to
`training_report.json` in the model directory:

```json
{
  "final_loss": 2.13,
  "training_samples": 420,
  "training_duration_formatted": "0:04:12",
  "device": "cpu"
}
```

A lower loss generally means the model fit your text better — but it is **not**
a measure of task accuracy.

## Benchmarking throughput and samples

For a richer, code-level look, the lower-level `ModelManager` and `ModelTrainer`
expose helpers:

```python
from buddy.train import ModelManager
import os

mgr = ModelManager()
mgr.load_model(os.path.expanduser("~/.buddy/trained_models/my-model"))

# Generation throughput + sample outputs (JSON string)
print(mgr.benchmark_model([
    "What is artificial intelligence?",
    "Explain machine learning.",
]))
```

`benchmark_model` reports `generation_time`, `tokens_generated`, and
`tokens_per_second` per prompt, plus aggregate `avg_tokens_per_second`.
`ModelTrainer.validate_model(test_prompts=[...])` similarly returns generated
text, `avg_generation_time`, and a `success_rate` (fraction of prompts that
generated without error).

!!! tip "Judge quality with an agent"
    Because these models are small and trained on raw text, the most useful
    "evaluation" is reading their generations for your use case. To score them
    systematically, wrap the model as an [Agent](training.md#using-a-trained-model-as-an-agent)
    and run it through the [Evaluation System](../advanced/evaluation.md) or
    [Competency Engine](../advanced/competency.md).
