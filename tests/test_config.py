from finlens.config import Settings


def test_masked_dict_redacts_sensitive_values() -> None:
    settings = Settings(
        aws_access_key_id="abc123",
        aws_secret_access_key="secret-value",
        fred_api_key="fred-secret",
        finlens_environment="test",
    )

    masked = settings.as_masked_dict(
        ["aws_access_key_id", "aws_secret_access_key", "fred_api_key", "finlens_environment"]
    )

    assert masked["aws_access_key_id"] == "***"
    assert masked["aws_secret_access_key"] == "***"
    assert masked["fred_api_key"] == "***"
    assert masked["finlens_environment"] == "test"


def test_require_raises_for_missing_variables() -> None:
    settings = Settings(fred_api_key=None, _env_file=None)

    try:
        settings.require("fred_api_key")
    except ValueError as exc:
        assert "fred_api_key" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing variable")


def test_active_source_list_normalises_csv_values() -> None:
    settings = Settings(finlens_active_sources=" fdic, FRED ,qbp ")

    assert settings.active_source_list == ["fdic", "fred", "qbp"]


def test_missing_or_placeholder_detects_placeholder_values() -> None:
    settings = Settings(
        fred_api_key="replace-me",
        cloudflare_api_token="your-value-here",
    )

    assert settings.missing_or_placeholder("fred_api_key", "cloudflare_api_token") == [
        "fred_api_key",
        "cloudflare_api_token",
    ]
