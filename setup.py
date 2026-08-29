#!/usr/bin/env python3
"""Editable install for C:\\Projects\\buddy as the `buddy` package."""
from pathlib import Path
from setuptools import setup

ROOT = Path(__file__).parent
SKIP_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "tests", "dist", "build",
    ".egg-info", "buddy_ai.egg-info", "buddy_ai.egg-info",
}

packages = ["buddy"]
for init in ROOT.rglob("__init__.py"):
    rel = init.parent.relative_to(ROOT)
    if rel == Path("."):
        continue
    parts = rel.parts
    if any(p in SKIP_DIRS or p.endswith(".egg-info") or p.startswith(".") for p in parts):
        continue
    packages.append("buddy." + ".".join(parts))

setup(
    name="buddy-ai",
    version="2.2.3",
    description="Buddy AI agent framework",
    package_dir={"buddy": "."},
    packages=sorted(set(packages)),
    python_requires=">=3.10",
    include_package_data=True,
)
