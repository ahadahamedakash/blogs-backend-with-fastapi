from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, register_user, login_user


@pytest.mark.anyio
async def test_register_user_validation_error(client: AsyncClient):
    response = await client.post(
        "/api/users",
        json={
            "username": "testuser",
        },
    )

    assert response.status_code == 422
    assert "email" in response.text
    assert "password" in response.text


@pytest.mark.anyio
async def test_register_user_duplicate_email(client: AsyncClient):
    await register_user(client)

    response = await client.post(
        "/api/users",
        json={
            "username": "different_user",
            "email": "testuser@gmail.com",
            "password": "testuser1234",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


@pytest.mark.anyio
async def test_create_user_success(client: AsyncClient):
    response = await client.post(
        "/api/users",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "securepassword123",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "image_path" in data
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.anyio
async def test_forgot_password_sends_email(client: AsyncClient):
    await register_user(client, email="test@example.com")

    with patch(
        "routers.users.send_password_reset_email",
        new_callable=AsyncMock,
    ) as mock_send:
        response = await client.post(
            "/api/users/forgot-password",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 202
        mock_send.assert_awaited_once()
        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["to_email"] == "test@example.com"
        assert call_kwargs["username"] == "testuser"
        assert "token" in call_kwargs
