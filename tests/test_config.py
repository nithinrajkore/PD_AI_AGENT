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
        "VOYAGE_API_KEY",
        "PD_AGENT_VOYAGE_API_KEY",
        "PD_AGENT_VOYAGE_EMBEDDING_MODEL",
        "COHERE_API_KEY",
        "PD_AGENT_COHERE_API_KEY",
        "PD_AGENT_COHERE_RERANK_MODEL",
        "PD_AGENT_RAG_CORPUS_DIR",
        "PD_AGENT_RAG_INDEX_DIR",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)


def test_defaults(clean_env):
    settings = PDAgentSettings()
    assert settings.anthropic_api_key is None
    assert settings.anthropic_model == "claude-sonnet-4-5"
    assert settings.openlane_bin == "openlane"
    assert settings.openlane2_repo == Path.home() / "Documents" / "Projects" / "openlane2"
    assert settings.voyage_api_key is None
    assert settings.voyage_embedding_model == "voyage-3-lite"
    assert settings.cohere_api_key is None
    assert settings.cohere_rerank_model == "rerank-v3.5"
    assert settings.rag_corpus_dir == Path("data/corpus")
    assert settings.rag_index_dir == Path("data/index")


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


def test_voyage_api_key_from_standard_env(clean_env, monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "pa-voyage-test-123")
    settings = PDAgentSettings()
    assert isinstance(settings.voyage_api_key, SecretStr)
    assert settings.voyage_api_key.get_secret_value() == "pa-voyage-test-123"


def test_voyage_api_key_from_prefixed_env(clean_env, monkeypatch):
    monkeypatch.setenv("PD_AGENT_VOYAGE_API_KEY", "pa-voyage-prefixed")
    settings = PDAgentSettings()
    assert settings.voyage_api_key is not None
    assert settings.voyage_api_key.get_secret_value() == "pa-voyage-prefixed"


def test_voyage_standard_env_wins_over_prefixed(clean_env, monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "standard-voyage")
    monkeypatch.setenv("PD_AGENT_VOYAGE_API_KEY", "prefixed-voyage")
    settings = PDAgentSettings()
    assert settings.voyage_api_key is not None
    assert settings.voyage_api_key.get_secret_value() == "standard-voyage"


def test_voyage_embedding_model_override(clean_env, monkeypatch):
    monkeypatch.setenv("PD_AGENT_VOYAGE_EMBEDDING_MODEL", "voyage-3")
    settings = PDAgentSettings()
    assert settings.voyage_embedding_model == "voyage-3"


def test_cohere_api_key_from_standard_env(clean_env, monkeypatch):
    monkeypatch.setenv("COHERE_API_KEY", "cohere-trial-xyz")
    settings = PDAgentSettings()
    assert isinstance(settings.cohere_api_key, SecretStr)
    assert settings.cohere_api_key.get_secret_value() == "cohere-trial-xyz"


def test_cohere_api_key_from_prefixed_env(clean_env, monkeypatch):
    monkeypatch.setenv("PD_AGENT_COHERE_API_KEY", "cohere-prefixed")
    settings = PDAgentSettings()
    assert settings.cohere_api_key is not None
    assert settings.cohere_api_key.get_secret_value() == "cohere-prefixed"


def test_cohere_rerank_model_override(clean_env, monkeypatch):
    monkeypatch.setenv("PD_AGENT_COHERE_RERANK_MODEL", "rerank-english-v3.0")
    settings = PDAgentSettings()
    assert settings.cohere_rerank_model == "rerank-english-v3.0"


def test_rag_dirs_override(clean_env, monkeypatch, tmp_path):
    custom_corpus = tmp_path / "my-corpus"
    custom_index = tmp_path / "my-index"
    monkeypatch.setenv("PD_AGENT_RAG_CORPUS_DIR", str(custom_corpus))
    monkeypatch.setenv("PD_AGENT_RAG_INDEX_DIR", str(custom_index))
    settings = PDAgentSettings()
    assert settings.rag_corpus_dir == custom_corpus
    assert settings.rag_index_dir == custom_index


def test_voyage_and_cohere_keys_hidden_in_repr(clean_env, monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "voyage-top-secret")
    monkeypatch.setenv("COHERE_API_KEY", "cohere-top-secret")
    settings = PDAgentSettings()
    rendered = repr(settings) + str(settings)
    assert "voyage-top-secret" not in rendered
    assert "cohere-top-secret" not in rendered
