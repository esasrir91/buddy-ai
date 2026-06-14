"""
Unit tests for pyproject.toml metadata — version sync and optional extras.
"""

import re
import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).parent.parent.parent / "pyproject.toml"


def load_pyproject():
    with open(PYPROJECT, "rb") as f:
        return tomllib.load(f)


def test_pyproject_version_matches_init():
    import buddy

    data = load_pyproject()
    pyproject_version = data["project"]["version"]
    assert pyproject_version == buddy.__version__, (
        f"pyproject.toml version ({pyproject_version}) " f"does not match buddy.__version__ ({buddy.__version__})"
    )


def test_pyproject_version_is_semver():
    data = load_pyproject()
    version = data["project"]["version"]
    assert re.match(r"^\d+\.\d+\.\d+$", version), f"version '{version}' is not valid semver (MAJOR.MINOR.PATCH)"


def test_training_extra_exists():
    data = load_pyproject()
    extras = data["project"].get("optional-dependencies", {})
    assert "training" in extras, "Missing [training] optional extra"
    training_deps = extras["training"]
    dep_names = [d.split(">=")[0].split("[")[0] for d in training_deps]
    assert "torch" in dep_names
    assert "transformers" in dep_names


def test_multimodal_extra_exists():
    data = load_pyproject()
    extras = data["project"].get("optional-dependencies", {})
    assert "multimodal" in extras, "Missing [multimodal] optional extra"
    multimodal_deps = extras["multimodal"]
    dep_names = [d.split(">=")[0].split("[")[0] for d in multimodal_deps]
    assert "Pillow" in dep_names or "pillow" in [d.lower() for d in dep_names]


def test_dev_extra_includes_pytest_cov():
    data = load_pyproject()
    extras = data["project"].get("optional-dependencies", {})
    assert "dev" in extras
    dev_deps = " ".join(extras["dev"])
    assert "pytest-cov" in dev_deps


def test_package_name_is_buddy_ai():
    data = load_pyproject()
    assert data["project"]["name"] == "buddy-ai"
