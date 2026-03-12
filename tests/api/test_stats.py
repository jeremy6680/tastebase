# tests/api/test_stats.py

"""Tests for the /stats endpoints."""

from fastapi.testclient import TestClient


class TestCounts:
    def test_counts_all_domains(self, client: TestClient) -> None:
        resp = client.get("/stats/counts")
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == {"music", "book", "manga", "movie", "series", "anime"}
        assert all(v == 1 for v in data.values())


class TestTopRated:
    def test_returns_top_rated(self, client: TestClient) -> None:
        resp = client.get("/stats/top-rated")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) > 0
        # All seeded items have rating 4 or 5 — first should be 5
        assert items[0]["rating"] == 5

    def test_filter_by_domain(self, client: TestClient) -> None:
        resp = client.get("/stats/top-rated?domain=music")
        assert resp.status_code == 200
        items = resp.json()
        assert all(i["domain"] == "music" for i in items)

    def test_limit(self, client: TestClient) -> None:
        resp = client.get("/stats/top-rated?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) <= 2


class TestTasteProfile:
    def test_returns_profile(self, client: TestClient) -> None:
        resp = client.get("/stats/taste-profile")
        assert resp.status_code == 200
        assert "profile" in resp.json()


class TestRecent:
    def test_returns_recent(self, client: TestClient) -> None:
        resp = client.get("/stats/recent")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_limit(self, client: TestClient) -> None:
        resp = client.get("/stats/recent?limit=3")
        assert resp.status_code == 200
        assert len(resp.json()) <= 3


class TestHealth:
    def test_health(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}