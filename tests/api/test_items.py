# tests/api/test_items.py

"""Tests for the /items endpoints."""

import hashlib

import pytest
from fastapi.testclient import TestClient


def _make_item_id(domain: str, source: str, title: str) -> str:
    return hashlib.sha256(f"{domain}:{source}:{title}".encode()).hexdigest()


class TestListItems:
    def test_returns_all_items(self, client: TestClient) -> None:
        resp = client.get("/items/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 6
        assert len(data["items"]) == 6

    def test_filter_by_domain(self, client: TestClient) -> None:
        resp = client.get("/items/?domain=music")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["domain"] == "music"

    def test_filter_by_min_rating(self, client: TestClient) -> None:
        resp = client.get("/items/?min_rating=5")
        assert resp.status_code == 200
        data = resp.json()
        # All seeded items have rating 5 except "book" (rating 4)
        assert data["total"] == 5

    def test_pagination(self, client: TestClient) -> None:
        resp = client.get("/items/?page=1&page_size=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 6


class TestGetItem:
    def test_existing_item(self, client: TestClient) -> None:
        item_id = _make_item_id("music", "musicbuddy", "Kind of Blue")
        resp = client.get(f"/items/{item_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Kind of Blue"
        assert data["domain"] == "music"
        assert data["rating"] == 5

    def test_not_found(self, client: TestClient) -> None:
        resp = client.get("/items/doesnotexist")
        assert resp.status_code == 404


class TestCreateItem:
    def test_create_item_without_rating(self, client: TestClient) -> None:
        payload = {
            "domain": "book",
            "source": "manual",
            "title": "The Name of the Wind",
            "creator": "Patrick Rothfuss",
            "year": 2007,
        }
        resp = client.post("/items/", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "The Name of the Wind"
        assert data["rating"] is None

    def test_create_item_with_rating(self, client: TestClient) -> None:
        payload = {
            "domain": "manga",
            "source": "manual",
            "title": "Vinland Saga",
            "creator": "Makoto Yukimura",
            "rating": 5,
        }
        resp = client.post("/items/", json=payload)
        assert resp.status_code == 201
        assert resp.json()["rating"] == 5

    def test_duplicate_returns_409(self, client: TestClient) -> None:
        payload = {"domain": "music", "source": "musicbuddy", "title": "Kind of Blue"}
        resp = client.post("/items/", json=payload)
        assert resp.status_code == 409


class TestUpdateItem:
    def test_update_title(self, client: TestClient) -> None:
        item_id = _make_item_id("book", "bookbuddy", "Dune")
        resp = client.patch(f"/items/{item_id}", json={"creator": "F. Herbert"})
        assert resp.status_code == 200
        assert resp.json()["creator"] == "F. Herbert"

    def test_update_not_found(self, client: TestClient) -> None:
        resp = client.patch("/items/doesnotexist", json={"title": "Ghost"})
        assert resp.status_code == 404