import os
import subprocess
import pytest
import requests

LOG_API_URL = os.getenv("LOG_API_URL", "http://localhost:8005")


@pytest.fixture(scope="module", autouse=True)
def ensure_log_services_running():
    subprocess.run(
        ["docker", "compose", "up", "-d", "--wait", "log-db", "log-service"],
        check=True,
    )


def test_create_and_read_audit_log():
    payload = {
        "actor_id": "analista_01",
        "actor_role": "ANALISTA",
        "action": "UPLOAD_LOTE",
        "resource": "lote_sintetico_001",
        "status": "SUCCESS",
        "details": {"registros": 100},
    }
    resp = requests.post(f"{LOG_API_URL}/logs/audit", json=payload, timeout=5)
    assert resp.status_code == 201
    created = resp.json()

    list_resp = requests.get(f"{LOG_API_URL}/logs/audit?limit=10", timeout=5)
    assert list_resp.status_code == 200
    assert any(item["event_id"] == created["event_id"] for item in list_resp.json())


def test_api_rejects_update_and_delete():
    assert requests.delete(f"{LOG_API_URL}/logs/audit/1", timeout=5).status_code in (404, 405)
    assert requests.put(f"{LOG_API_URL}/logs/audit/1", json={}, timeout=5).status_code in (404, 405)
    assert requests.patch(f"{LOG_API_URL}/logs/audit/1", json={}, timeout=5).status_code in (404, 405)


def test_direct_db_rejects_update_and_delete():
    resp = requests.post(
        f"{LOG_API_URL}/logs/audit",
        json={
            "actor_id": "tester_cq01",
            "actor_role": "ANALISTA",
            "action": "TESTE_IMUTABILIDADE",
            "resource": "audit_logs",
            "status": "SUCCESS",
        },
        timeout=5,
    )
    assert resp.status_code == 201
    log_id = resp.json()["id"]

    update_cmd = [
        "docker", "compose", "exec", "-T", "log-db",
        "psql", "-U", "log_admin", "-d", "segurasaude_logs",
        "-c", f"UPDATE audit_logs SET action = 'FRAUDE' WHERE id = {log_id};",
    ]
    delete_cmd = [
        "docker", "compose", "exec", "-T", "log-db",
        "psql", "-U", "log_admin", "-d", "segurasaude_logs",
        "-c", f"DELETE FROM audit_logs WHERE id = {log_id};",
    ]

    res_update = subprocess.run(update_cmd, capture_output=True, text=True)
    res_delete = subprocess.run(delete_cmd, capture_output=True, text=True)

    assert res_update.returncode != 0
    assert "Operação proibida" in res_update.stderr
    assert res_delete.returncode != 0
    assert "Operação proibida" in res_delete.stderr
