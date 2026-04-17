"""Smoke tests: verify package installs and imports cleanly."""

import pd_agent


def test_package_imports() -> None:
    assert pd_agent is not None


def test_version_is_string() -> None:
    assert isinstance(pd_agent.__version__, str)
    assert pd_agent.__version__ == "0.1.0"
