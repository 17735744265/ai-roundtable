"""E2E: Full API flow — session CRUD, guest list, multi-session isolation."""

import json
import pytest
import pytest_asyncio


class TestGuestListAPI:
    """GET /api/experts — should return preset guests."""

    @pytest.mark.asyncio
    async def test_get_guests_returns_list(self, async_client):
        resp = await async_client.get("/api/experts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert len(data["data"]) == 6

    @pytest.mark.asyncio
    async def test_guests_have_required_fields(self, async_client):
        resp = await async_client.get("/api/experts")
        guests = resp.json()["data"]
        for g in guests:
            assert "id" in g
            assert "name" in g
            assert "avatar" in g
            assert "description" in g


class TestSessionCRUD:
    """POST/GET/DELETE /api/discussion/* — full lifecycle."""

    @pytest.mark.asyncio
    async def test_create_session_success(self, async_client):
        body = {
            "topic": "E2E测试话题",
            "host": {"id": "moderator", "name": "主持人", "title": "主持人",
                     "stance": "中立", "avatar": "🎤", "color": "#F59E0B"},
            "experts": [
                {"id": "expert_0", "name": "张明", "title": "顾问", "stance": "支持",
                 "avatar": "💼", "color": "#3B82F6"},
                {"id": "expert_1", "name": "李婷", "title": "分析师", "stance": "质疑",
                 "avatar": "📊", "color": "#EF4444"},
            ],
        }
        resp = await async_client.post("/api/discussion/start", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["status"] == "active"
        assert len(data["data"]["guests"]) == 3  # host + 2 experts
        return data["data"]["id"]

    @pytest.mark.asyncio
    async def test_get_session_detail(self, async_client):
        # Create first
        body = {
            "topic": "详情测试",
            "host": {"id": "moderator", "name": "主持", "title": "T", "stance": "S",
                     "avatar": "🎤", "color": "#000"},
            "experts": [
                {"id": "expert_0", "name": "专家A", "title": "T1", "stance": "S1",
                 "avatar": "A", "color": "#111"},
                {"id": "expert_1", "name": "专家B", "title": "T2", "stance": "S2",
                 "avatar": "B", "color": "#222"},
            ],
        }
        create_resp = await async_client.post("/api/discussion/start", json=body)
        sid = create_resp.json()["data"]["id"]

        resp = await async_client.get(f"/api/discussions/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["topic"] == "详情测试"
        assert data["data"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_list_sessions_with_filter(self, async_client):
        resp = await async_client.get("/api/discussions?status_filter=active")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data["data"]
        assert "total" in data["data"]

    @pytest.mark.asyncio
    async def test_delete_session(self, async_client):
        # Create
        body = {
            "topic": "删除测试",
            "host": {"id": "moderator", "name": "主持", "title": "T", "stance": "S",
                     "avatar": "🎤", "color": "#000"},
            "experts": [
                {"id": "expert_0", "name": "X", "title": "T", "stance": "S",
                 "avatar": "A", "color": "#111"},
                {"id": "expert_1", "name": "Y", "title": "T", "stance": "S",
                 "avatar": "B", "color": "#222"},
            ],
        }
        create_resp = await async_client.post("/api/discussion/start", json=body)
        sid = create_resp.json()["data"]["id"]

        # Can't delete active session
        resp = await async_client.delete(f"/api/discussions/{sid}")
        assert resp.status_code == 409  # Conflict — session is active

    @pytest.mark.asyncio
    async def test_health_check(self, async_client):
        resp = await async_client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestMultiSessionIsolation:
    """Verify concurrent sessions have isolated state."""

    async def test_sessions_have_different_ids(self, async_client):
        body1 = {
            "topic": "Session 1",
            "host": {"id": "moderator", "name": "H", "title": "T", "stance": "S",
                     "avatar": "🎤", "color": "#000"},
            "experts": [
                {"id": "e0", "name": "A", "title": "T", "stance": "S", "avatar": "a", "color": "#111"},
                {"id": "e1", "name": "B", "title": "T", "stance": "S", "avatar": "b", "color": "#222"},
            ],
        }
        body2 = {**body1, "topic": "Session 2"}

        r1 = await async_client.post("/api/discussion/start", json=body1)
        r2 = await async_client.post("/api/discussion/start", json=body2)

        id1 = r1.json()["data"]["id"]
        id2 = r2.json()["data"]["id"]
        assert id1 != id2

        # Each session has its own detail
        d1 = await async_client.get(f"/api/discussions/{id1}")
        d2 = await async_client.get(f"/api/discussions/{id2}")
        assert d1.json()["data"]["topic"] == "Session 1"
        assert d2.json()["data"]["topic"] == "Session 2"

    async def test_active_sessions_list(self, async_client):
        resp = await async_client.get("/api/discussions?status_filter=active")
        assert resp.status_code == 200
        # Should list previously created sessions
        assert resp.json()["data"]["total"] >= 2


class TestValidation:
    """Input validation — verify schema constraints."""

    async def test_create_session_empty_topic(self, async_client):
        body = {
            "topic": "",
            "host": {"id": "m", "name": "H", "title": "T", "stance": "S",
                     "avatar": "🎤", "color": "#000"},
            "experts": [
                {"id": "e0", "name": "A", "title": "T", "stance": "S", "avatar": "a", "color": "#111"},
                {"id": "e1", "name": "B", "title": "T", "stance": "S", "avatar": "b", "color": "#222"},
            ],
        }
        resp = await async_client.post("/api/discussion/start", json=body)
        assert resp.status_code == 422  # Pydantic validation error

    async def test_create_session_too_few_experts(self, async_client):
        body = {
            "topic": "测试",
            "host": {"id": "m", "name": "H", "title": "T", "stance": "S",
                     "avatar": "🎤", "color": "#000"},
            "experts": [
                {"id": "e0", "name": "A", "title": "T", "stance": "S", "avatar": "a", "color": "#111"},
            ],
        }
        resp = await async_client.post("/api/discussion/start", json=body)
        assert resp.status_code == 422  # min_length=2
