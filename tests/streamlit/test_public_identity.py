import json

from streamlit_app.lib import public_identity as identity_module


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_loads_central_portfolio_identity(monkeypatch) -> None:
    payload = {
        "identity": {
            "display_name": "Surya Vaddhiparthy",
            "portfolio_url": "https://vaddhiparthy.com/",
            "github_url": "https://github.com/vaddhiparthy/",
        }
    }
    monkeypatch.setattr(identity_module, "urlopen", lambda *_args, **_kwargs: _Response(payload))

    identity = identity_module._load_public_identity("http://portfolio/data/site-content.json")

    assert identity.display_name == "Surya Vaddhiparthy"
    assert identity.portfolio_url == "https://vaddhiparthy.com/"
    assert identity.github_url == "https://github.com/vaddhiparthy/"


def test_applies_central_identity_to_current_urls(monkeypatch) -> None:
    monkeypatch.setattr(
        identity_module,
        "public_identity",
        lambda: identity_module.PublicIdentity(
            "Example Name",
            "https://example.test/",
            "https://github.com/example/",
        ),
    )

    rendered = identity_module.apply_public_identity(
        "Surya Vaddhiparthy https://vaddhiparthy.com/x "
        "https://github.com/vaddhiparthy/project"
    )

    assert rendered == "Example Name https://example.test/x https://github.com/example/project"
