"""
Unit tests for buddy/__init__.py — package metadata and feature flags.
"""


def test_version_is_string():
    import buddy

    assert isinstance(buddy.__version__, str)


def test_version_matches_semver():
    import buddy

    parts = buddy.__version__.split(".")
    assert len(parts) >= 2, "version should be semver (MAJOR.MINOR.PATCH)"
    assert all(p.isdigit() for p in parts), "all version parts should be numeric"


def test_version_is_not_dev_local():
    import buddy

    assert buddy.__version__ != "dev-local", (
        "buddy.__version__ returned 'dev-local'. " "Check that pyproject.toml version matches __init__.py."
    )


def test_core_exports_present():
    import buddy

    assert hasattr(buddy, "Agent"), "buddy.Agent should be exported"
    assert hasattr(buddy, "Team"), "buddy.Team should be exported"
    assert hasattr(buddy, "Model"), "buddy.Model should be exported"
    assert hasattr(buddy, "Toolkit"), "buddy.Toolkit should be exported"
    assert hasattr(buddy, "Function"), "buddy.Function should be exported"


def test_features_dict_structure():
    import buddy

    features = buddy.__features__
    assert isinstance(features, dict)
    assert "core" in features
    assert features["core"] is True


def test_get_available_features_returns_list():
    import buddy

    result = buddy.get_available_features()
    assert isinstance(result, list)
    assert "core" in result


def test_check_feature_known():
    import buddy

    assert buddy.check_feature("core") is True


def test_check_feature_unknown():
    import buddy

    assert buddy.check_feature("nonexistent_feature_xyz") is False


def test_get_version_info_structure():
    import buddy

    info = buddy.get_version_info()
    assert isinstance(info, dict)
    assert "version" in info
    assert "features" in info
    assert "available_features" in info
    assert "author" in info
