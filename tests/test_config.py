"""Tests for :class:`pd_agent.config.PDAgentSettings`."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr

from pd_agent.config import PDAgentSettings


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    """Clear any host env vars that could leak into settings, and chdir to tmp.

    Running the settings constructor in a clean environment keeps these tests
    hermetic — otherwise a user with ``ANTHROPIC_API_KEY`` exported in their
    shell would see surprising results.
    """
    for var in (
        "ANTHROPIC_API_KEY",
        "PD_AGENT_ANTHROPIC_API_KEY",
        "PD_AGENT_ANTHROPIC_MODEL",
        "PD_AGENT_OPENLANE2_REPO",
        "PD_AGENT_OPENLANE_BIN",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)


def test_defaults(clean_env):
    settings = PDAgentSettings()
    assert settings.anthropic_api_key is None
    assert settings.anthropic_model == "claude-sonnet-4-5"
    assert settings.openlane_bin == "openlane"
    assert settings.openlane2_repo == Path.home() / "Documents" / "Projects" / "openlane2"


def test_anthropic_api_key_from_standard_env(clean_env, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-12345")
    settings = PDAgentSettings()
    assert isinstance(settings.anthropic_api_key, SecretStr)
    assert settings.anthropic_api_key.get_secret_value() == "sk-ant-test-12345"


def test_anthropic_api_key_from_prefixed_env(clean_env, monkeypatch):
    monkeypatch.setenv("PD_AGENT_ANTHROPIC_API_KEY", "sk-ant-prefixed")
    settings = PDAgentSettings()
    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "sk-ant-prefixed"


def test_standard_env_wins_over_prefixed(clean_env, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "standard")
    monkeypatch.setenv("PD_AGENT_ANTHROPIC_API_KEY", "prefixed")
    settings = PDAgentSettings()
    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "standard"


def test_anthropic_api_key_from_dotenv(clean_env, tmp_path):
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=from-dotenv\n")
    settings = PDAgentSettings()
    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "from-dotenv"


def test_anthropic_model_override(clean_env, monkeypatch):
    monkeypatch.setenv("PD_AGENT_ANTHROPIC_MODEL", "claude-opus-4-5")
    settings = PDAgentSettings()
    assert settings.anthropic_model == "claude-opus-4-5"


def test_secret_str_hides_value_in_repr(clean_env, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret-abc")
    settings = PDAgentSettings()
    assert "sk-ant-secret-abc" not in repr(settings)
    assert "sk-ant-secret-abc" not in str(settings)
