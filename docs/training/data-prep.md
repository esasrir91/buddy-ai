# Data Preparation

Before training, your raw files are turned into clean text chunks by
`DataProcessor` (`buddy.train.data_processor`). You rarely call it directly —
`train_model` runs it for you — but understanding what it accepts helps you
assemble a good dataset.

!!! tip "Just point it at a folder"
    `DataProcessor` traverses a directory **recursively** and tries to read
    *every* file as text. There is no required format or schema: drop your
    `.txt`, `.md`, `.csv`, `.json`, `.pdf`, and `.docx` files into a folder and
    train on it.

## What it accepts

`DataProcessor.process_directory(path)` walks the directory and, for each file:

1. Skips hidden files, files over 100 MB, and known **binary** formats (images,
   archives, executables, etc.) detected via magic-number signatures.
2. Extracts text using a specialized reader when available:
    - **PDF** via `pdfplumber`, falling back to `PyPDF2`
    - **DOCX** via `python-docx` (paragraphs *and* tables)
3. Otherwise reads the file as text, auto-detecting the encoding.

### Encoding detection

Text files don't need to be UTF-8. The processor first tries `chardet`, then
falls back through a long list of encodings (`utf-8`, `utf-16`, `latin-1`,
`cp1252`, `shift_jis`, `gb2312`, `big5`, and more), and finally decodes with
`errors="ignore"` as a last resort. Files it genuinely cannot read are skipped.

## How it cleans and chunks

Each extracted text is normalized by `_clean_text`:

- Control characters are stripped.
- Repeated spaces/tabs collapse to a single space.
- Three-or-more blank lines collapse to a double newline.
- Whitespace-only lines are removed.

Texts shorter than `min_text_length` (default **10** characters) are dropped.
Longer texts are split on word boundaries into chunks no larger than
`max_text_length` (default **10000** characters).

```python
from buddy.train import DataProcessor

processor = DataProcessor(min_text_length=10, max_text_length=10000)
data = processor.process_directory("/path/to/data")

print(f"Texts: {len(data.texts)}")
print(f"Stats: {data.stats}")
```

## The `ProcessedData` result

`process_directory` returns a `ProcessedData` dataclass with three fields:

| Field | Type | Contents |
|-------|------|----------|
| `texts` | `List[str]` | The cleaned, chunked text used for training |
| `metadata` | `List[Dict]` | Per-chunk info: source file, file type, encoding, chunk index, char/word counts |
| `stats` | `Dict` | Totals: `processed_files`, `skipped_files`, `total_characters`, `avg_text_length`, plus encoding/file-type distributions |

## Saving and reloading

You can persist processed data to JSON and load it later — useful for
reproducible runs or inspecting what was extracted:

```python
processor.save_processed_data(data, "processed.json")
data = processor.load_processed_data("processed.json")
```

!!! warning "Training is unsupervised text"
    Fine-tuning here is **causal language modeling** over your raw text — there
    is no instruction/response labeling step. To bias the model toward a
    conversational style, include text that already reads like the
    dialogue you want.

## Next steps

- [Model Training](training.md) — turn `ProcessedData` into a trained model
