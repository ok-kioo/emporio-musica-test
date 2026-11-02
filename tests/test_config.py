from datetime import date

from src import config


def test_store_contact_configuration_is_centralized() -> None:
    assert config.STORE_SUPPORT_PHONE == "(67) 3341-4444"
    assert config.ASSISTANT_PHONE == "(67) 3321-4500"
    assert config.STORE_EMAIL == "contato@emporiodamusica.com.br"


def test_reference_date_is_fixed_and_reproducible() -> None:
    assert config.REFERENCE_DATE == date(2025, 6, 16)
