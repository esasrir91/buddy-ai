#!/bin/bash
set -euxo pipefail
pip install --upgrade pip
pip install -e ".[dev]" --no-cache-dir
python -c "import buddy; print('buddy', buddy.__version__)"
python -c "from buddy.cli.entrypoint import BUDDY_cli; print('cli ok')"
