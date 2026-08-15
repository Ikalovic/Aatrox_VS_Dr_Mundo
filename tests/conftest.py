import pytest


@pytest.fixture
def app(tmp_path):
    from app import create_app

    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "game.db"), "FLAG": "flag{test}"})


@pytest.fixture
def client(app):
    return app.test_client()
