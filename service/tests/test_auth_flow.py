"""End-to-end smoke test for the auth flow (REST resource routes).

Requires a live PostgreSQL matching DATABASE_URL (from .env or the default in
app.core.config), with `alembic upgrade head` already applied. Run with:

    uv run pytest
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_register_login_me_refresh():
    suffix = uuid.uuid4().hex[:8]
    username = f"user_{suffix}"
    email = f"user_{suffix}@example.com"
    password = "supersecret1"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        # POST /users -> create user (201)
        r = await ac.post(
            "/users",
            json={"username": username, "email": email, "password": password},
        )
        assert r.status_code == 201, r.text
        assert r.json()["username"] == username

        # duplicate create -> 409
        r = await ac.post(
            "/users",
            json={"username": username, "email": email, "password": password},
        )
        assert r.status_code == 409

        # POST /tokens -> login by username (200)
        r = await ac.post("/tokens", data={"username": username, "password": password})
        assert r.status_code == 200, r.text
        access, refresh = r.json()["access_token"], r.json()["refresh_token"]

        # login by email also works (200)
        r = await ac.post("/tokens", data={"username": email, "password": password})
        assert r.status_code == 200

        # GET /users/me with access token (200)
        r = await ac.get("/users/me", headers={"Authorization": f"Bearer {access}"})
        assert r.status_code == 200 and r.json()["username"] == username

        # GET /users/me without token (401)
        assert (await ac.get("/users/me")).status_code == 401

        # a refresh token must not be accepted as an access token (401)
        r = await ac.get("/users/me", headers={"Authorization": f"Bearer {refresh}"})
        assert r.status_code == 401

        # POST /tokens/refresh -> rotate (200)
        r = await ac.post("/tokens/refresh", json={"refresh_token": refresh})
        assert r.status_code == 200, r.text
        new_refresh = r.json()["refresh_token"]

        # old refresh now revoked (401)
        r = await ac.post("/tokens/refresh", json={"refresh_token": refresh})
        assert r.status_code == 401

        # new refresh still valid (200)
        r = await ac.post("/tokens/refresh", json={"refresh_token": new_refresh})
        assert r.status_code == 200
