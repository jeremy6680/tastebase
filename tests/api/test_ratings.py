# tests/api/test_ratings.py

"""Tests for the /items/{item_id}/ratings endpoints."""

import hashlib

from fastapi.testclient import TestClient


def _make_item_id(domain: str, source: str, title: str) -> str:
    return hashlib.sha256(f"{domain}:{source}:{title}".encode()).hexdigest()


class TestGetRating:
    def test_rated_item(self, client: TestClient) -> None:
        item_id = _make_item_id("music", "musicbuddy", "Kind of Blue")
        resp = client.get(f"/items/{item_id}/ratings")
        assert resp.status_code == 200
        assert resp.json()["rating"] == 5

    def test_not_found(self, client: TestClient) -> None:
        resp = client.get("/items/doesnotexist/ratings")
        assert resp.status_code == 404


class TestUpsertRating:
    def test_update_existing_rating(self, client: TestClient) -> None:
        item_id = _make_item_id("book", "bookbuddy", "Dune")
        resp = client.post(f"/items/{item_id}/ratings", json={"rating": 5})
        assert resp.status_code == 201
        assert resp.json()["rating"] == 5
        assert resp.json()["source"] == "user"

    def test_add_rating_to_unrated_item(self, client: TestClient) -> None:
        # First create an unrated item
        create_resp = client.post(
            "/items/",
            json={"domain": "series", "source": "manual", "title": "Deadwood"},
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        rate_resp = client.post(f"/items/{item_id}/ratings", json={"rating": 4})
        assert rate_resp.status_code == 201
        assert rate_resp.json()["rating"] == 4

    def test_rating_out_of_range(self, client: TestClient) -> None:
        item_id = _make_item_id("music", "musicbuddy", "Kind of Blue")
        resp = client.post(f"/items/{item_id}/ratings", json={"rating": 6})
        assert resp.status_code == 422

    def test_not_found(self, client: TestClient) -> None:
        resp = client.post("/items/doesnotexist/ratings", json={"rating": 3})
        assert resp.status_code == 404


class TestRatingHistory:
    def test_history_after_update(self, client: TestClient) -> None:
        item_id = _make_item_id("manga", "bookbuddy", "Berserk")
        # Update rating to create a second event
        client.post(f"/items/{item_id}/ratings", json={"rating": 4})
        resp = client.get(f"/items/{item_id}/ratings/history")
        assert resp.status_code == 200
        events = resp.json()
        # At least the update event (seeded data doesn't have an event row)
        assert len(events) >= 1
        assert events[-1]["new_rating"] == 4