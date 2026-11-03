from datetime import date
from pathlib import Path

from src import config


def test_store_contact_configuration_is_centralized() -> None:
    assert config.STORE_SUPPORT_PHONE == "(67) 3341-4444"
    assert config.ASSISTANT_PHONE == "(67) 3321-4500"
    assert config.STORE_EMAIL == "contato@emporiodamusica.com.br"


def test_reference_date_is_fixed_and_reproducible() -> None:
    assert config.REFERENCE_DATE == date(2025, 6, 16)


def test_runtime_settings_expand_paths_and_keep_the_nvidia_text_model_default(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///$PWD/runtime.db")
    monkeypatch.setenv("POLICY_VECTOR_DIRECTORY", "$PWD/vectors")
    monkeypatch.delenv("OPENROUTER_TEXT_MODEL", raising=False)
    monkeypatch.setenv("PWD", str(tmp_path))

    settings = config.PolicyRuntimeSettings.from_environment(tmp_path)

    assert settings.database_url == f"sqlite:///{tmp_path}/runtime.db"
    assert settings.vector_directory == tmp_path / "vectors"
    assert settings.text_model == "nvidia/nemotron-3-ultra-550b-a55b:free"


def test_runtime_settings_load_dotenv_without_overriding_process_environment(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "OPENROUTER_API_KEY=from-dotenv\nOPENROUTER_TEXT_MODEL=dotenv-model\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_TEXT_MODEL", "process-model")

    settings = config.PolicyRuntimeSettings.from_environment(tmp_path)

    assert settings.text_api_key == "from-dotenv"
    assert settings.decision_api_key == "from-dotenv"
    assert settings.text_model == "process-model"
