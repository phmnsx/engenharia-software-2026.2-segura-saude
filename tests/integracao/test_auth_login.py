import base64
import json
import os
import subprocess

import pytest
import requests

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8080")


def _decode_jwt_payload(token: str) -> dict:
    payload_b64 = token.split(".")[1]
    padding = "=" * (-len(payload_b64) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b64 + padding))


@pytest.fixture(scope="module", autouse=True)
def ensure_gateway_running():
    subprocess.run(
        ["docker", "compose", "up", "-d", "--wait", "gateway-1", "gateway-2", "gateway-3", "nginx"],
        check=True,
    )


@pytest.mark.parametrize(
    "email,password,expected_role",
    [
        ("analista@segurasaude.local", "Analista@123", "ANALISTA"),
        ("dev@segurasaude.local", "Dev@123", "DESENVOLVEDOR"),
    ],
)
def test_login_returns_jwt_with_role_claim(email, password, expected_role):
    resp = requests.post(
        f"{GATEWAY_URL}/auth/login",
        json={"email": email, "password": password},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == expected_role

    claims = _decode_jwt_payload(body["access_token"])
    assert claims["role"] == expected_role
    assert claims["email"] == email


def test_login_invalid_credentials_returns_401():
    resp = requests.post(
        f"{GATEWAY_URL}/auth/login",
        json={"email": "analista@segurasaude.local", "password": "senha_errada"},
        timeout=5,
    )
    assert resp.status_code == 401


def test_me_endpoint_validates_jwt_across_cluster():
    login_resp = requests.post(
        f"{GATEWAY_URL}/auth/login",
        json={"email": "analista@segurasaude.local", "password": "Analista@123"},
        timeout=5,
    )
    token = login_resp.json()["access_token"]

    me_resp = requests.get(
        f"{GATEWAY_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "ANALISTA"
