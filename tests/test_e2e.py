"""End-to-end sanity checks for the documented HTTP API (see docs/api.md, docs/persistence.md).

Uses pytest and FastAPI's TestClient, both already available via the project's
existing dependencies (no extra packages required).
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from seriousdb import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A TestClient backed by a throwaway database file.

    Entered as a context manager so that the lifespan handler loads the database.
    """
    monkeypatch.setattr(main, "DB_FILE", str(tmp_path / ".sdb"))

    with TestClient(main.app) as test_client:
        yield test_client


def test_fresh_database_seeds_documented_default_key(client):
    # docs/persistence.md: a new database file is seeded with {"default": "default"}
    response = client.get("/db", params={"key": "default"})
    assert response.status_code == 200
    assert response.json() == "default"


def test_put_stores_value_and_get_retrieves_it(client):
    put_response = client.put("/db", params={"key": "name", "value": "Alice"})
    assert put_response.status_code == 200
    assert put_response.json() == "Alice"

    get_response = client.get("/db", params={"key": "name"})
    assert get_response.status_code == 200
    assert get_response.json() == "Alice"


def test_put_stores_value_and_head_checks_for_it(client):
    put_response = client.put("/db", params={"key": "name", "value": "Alice"})
    assert put_response.status_code == 200
    assert put_response.json() == "Alice"

    head_response = client.head("/db", params={"key": "name"})
    assert head_response.status_code == 200


def test_put_overwrites_existing_key(client):
    client.put("/db", params={"key": "name", "value": "Alice"})
    client.put("/db", params={"key": "name", "value": "Bob"})

    response = client.get("/db", params={"key": "name"})
    assert response.json() == "Bob"


def test_get_missing_key_returns_404(client):
    # docs/api.md: "If the requested key does not exist, the API returns a 404 response."
    response = client.get("/db", params={"key": "does-not-exist"})
    assert response.status_code == 404


def test_head_missing_key_returns_404(client):
    # docs/api.md: "If the requested key does not exist, the API returns a 404 response."
    response = client.head("/db", params={"key": "does-not-exist"})
    assert response.status_code == 404


def test_put_persists_to_db_file_on_disk(client):
    # docs/persistence.md: each PUT writes the complete dictionary back to disk.
    client.put("/db", params={"key": "name", "value": "Alice"})

    on_disk = json.loads(Path(main.DB_FILE).read_text())
    assert on_disk["name"] == "Alice"


def test_delete_existing_key_removes_it(client):
    put_response = client.put("/db", params={"key": "name", "value": "Alice"})
    assert put_response.status_code == 200

    delete_response = client.delete("/db", params={"key": "name"})
    assert delete_response.status_code == 200

    get_response = client.get("/db", params={"key": "name"})
    assert get_response.status_code == 404


def test_delete_missing_key_returns_404(client):
    response = client.delete("/db", params={"key": "does-not-exist"})
    assert response.status_code == 404
