"""TokenDetails must carry JWT only in the request body — never as
authorization metadata (HTTP Authorization). Finam AuthService contract:
POST /v1/sessions/details with {"token": "..."} and Content-Type only.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from finam_client.client import FinamApiClient
from finam_client.config import ClientConfig


@pytest.fixture
def grpc_client():
    with patch("finam_client.client.secure_channel") as secure_channel_mock:
        client = FinamApiClient(ClientConfig(secret_file="unused"), secret="secret")
        client._test_secure_channel_mock = secure_channel_mock
        yield client
        client.close()


def test_token_details_omits_authorization_metadata(grpc_client):
    captured: list[dict] = []

    def _token_details_with_call(**kwargs):
        captured.append(dict(kwargs))
        expires = datetime.now(timezone.utc) + timedelta(minutes=15)
        return SimpleNamespace(expires_at=expires, account_ids=["acc-1"], readonly=False), None

    grpc_client._jwt_token = "jwt-for-body"
    grpc_client._jwt_issued = int(datetime.now(timezone.utc).timestamp())
    grpc_client._jwt_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    grpc_client._metadata = ("authorization", "jwt-for-body")
    grpc_client.auth_stub.TokenDetails.with_call = _token_details_with_call

    response = grpc_client.token_details()

    assert response.account_ids == ["acc-1"]
    assert len(captured) == 1
    assert "metadata" not in captured[0]
    assert captured[0]["request"].token == "jwt-for-body"


def test_load_expires_at_omits_authorization_metadata(grpc_client):
    captured: list[dict] = []

    def _token_details_with_call(**kwargs):
        captured.append(dict(kwargs))
        expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        return SimpleNamespace(expires_at=expires), None

    grpc_client._jwt_token = "jwt-after-auth"
    grpc_client._metadata = ("authorization", "jwt-after-auth")
    grpc_client.auth_stub.TokenDetails.with_call = _token_details_with_call

    grpc_client._load_expires_at_from_token_details()

    assert len(captured) == 1
    assert "metadata" not in captured[0]
    assert captured[0]["request"].token == "jwt-after-auth"
    assert grpc_client._jwt_expires_at is not None


def test_jwt_expires_at_property(grpc_client):
    assert grpc_client.jwt_expires_at is None
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    grpc_client._jwt_expires_at = expires
    assert grpc_client.jwt_expires_at == expires
