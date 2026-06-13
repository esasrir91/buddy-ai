# Contributing to Buddy AI

Thank you for your interest in contributing to **Buddy AI**! Every contribution — bug reports,
feature requests, documentation improvements, and code — is appreciated.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)
- [Requesting Features](#requesting-features)

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
By participating, you agree to uphold these standards.

---

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/buddy-ai.git
   cd buddy-ai
   ```
3. **Create a branch** for your change:
   ```bash
   git checkout -b fix/my-bug-description
   # or
   git checkout -b feat/my-feature-name
   ```

---

## Development Setup

```bash
# Create a virtual environment (Python 3.10+)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install the package in editable mode with dev dependencies
pip install -e ".[dev]"

# Copy the environment variables template
cp .env.example .env
# Edit .env with your API keys as needed
```

---

## Running Tests

```bash
# Run all tests with coverage
pytest

# Run a specific test file
pytest tests/unit/test_agent.py -v

# Run tests without coverage (faster during development)
pytest --no-cov

# Run linting
flake8 buddy/ tests/

# Run type checking
mypy buddy/

# Format code
black buddy/ tests/
isort buddy/ tests/
```

---

## Code Style

- **Formatter:** [Black](https://black.readthedocs.io/) with `line-length = 120`
- **Import sorter:** [isort](https://pycqa.github.io/isort/) with `profile = "black"`
- **Type checker:** [mypy](https://mypy.readthedocs.io/) with `disallow_untyped_defs = true`
- **Linter:** [flake8](https://flake8.pycqa.org/)

All code must pass `black --check`, `isort --check-only`, `flake8`, and `mypy` before merge.

**Key conventions:**
- Use Pydantic v2 models for all data classes
- Add docstrings to all public methods (Google style)
- Write unit tests for every new public function or class
- Never commit API keys or secrets

---

## Submitting Changes

1. **Commit** your changes with a clear message:
   ```bash
   git commit -m "fix: correct version lookup in CLI get_app_version()"
   ```
   We follow [Conventional Commits](https://www.conventionalcommits.org/): `fix:`, `feat:`, `docs:`, `refactor:`, `test:`, `chore:`

2. **Push** to your fork:
   ```bash
   git push origin fix/my-bug-description
   ```

3. **Open a Pull Request** against the `main` branch. Describe what changed and why.

4. A maintainer will review your PR. Please respond to feedback within 7 days.

---

## Reporting Bugs

Open a [GitHub Issue](https://github.com/esasrir91/buddy-ai/issues/new?template=bug_report.md) and include:
- buddy-ai version (`buddy --version` or `python -c "import buddy; print(buddy.__version__)"`)
- Python version
- Operating system
- Minimal reproducible example
- Full traceback

---

## Requesting Features

Open a [GitHub Discussion](https://github.com/esasrir91/buddy-ai/discussions) or an
[Issue](https://github.com/esasrir91/buddy-ai/issues/new?template=feature_request.md).
Describe the use case and why the current API doesn't cover it.

---

## Questions?

Post in [GitHub Discussions](https://github.com/esasrir91/buddy-ai/discussions) or
open an issue tagged `question`.
