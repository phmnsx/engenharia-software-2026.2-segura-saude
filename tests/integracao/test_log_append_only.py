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


def test_cq01_imutabilidade_logs_bloqueio_alteracao_e_exclusao():
    """
    Cenário CQ01 (P3 - Seção 8 / ASR01 / RNF001):
    Valida que qualquer tentativa de alteração (UPDATE) ou exclusão (DELETE/TRUNCATE)
    diretamente no banco de dados falha com bloqueio e mantém 100% dos registros intactos.
    """
    # 1. Obter contagem inicial de registros
    count_cmd = [
        "docker", "compose", "exec", "-T", "log-db",
        "psql", "-U", "log_admin", "-d", "segurasaude_logs", "-t", "-A",
        "-c", "SELECT COUNT(*) FROM audit_logs;",
    ]
    initial_count = int(subprocess.run(count_cmd, capture_output=True, text=True, check=True).stdout.strip())

    # 2. Inserir registro de auditoria válido
    payload = {
        "actor_id": "tester_cq01",
        "actor_role": "ANALISTA",
        "action": "TESTE_IMUTABILIDADE_CQ01",
        "resource": "audit_logs",
        "status": "SUCCESS",
        "details": {"cenario": "CQ01", "tentativas_bloqueadas": ["UPDATE", "DELETE", "TRUNCATE"]},
    }
    resp = requests.post(f"{LOG_API_URL}/logs/audit", json=payload, timeout=5)
    assert resp.status_code == 201
    log_id = resp.json()["id"]
    event_id = resp.json()["event_id"]

    # 3. Tentar alteração (UPDATE) com usuário admin no banco -> deve falhar
    update_cmd = [
        "docker", "compose", "exec", "-T", "log-db",
        "psql", "-U", "log_admin", "-d", "segurasaude_logs",
        "-c", f"UPDATE audit_logs SET action = 'FRAUDE_CQ01' WHERE id = {log_id};",
    ]
    res_update = subprocess.run(update_cmd, capture_output=True, text=True)
    assert res_update.returncode != 0
    assert "Operação proibida" in res_update.stderr

    # 4. Tentar exclusão pontual (DELETE) com usuário admin no banco -> deve falhar
    delete_cmd = [
        "docker", "compose", "exec", "-T", "log-db",
        "psql", "-U", "log_admin", "-d", "segurasaude_logs",
        "-c", f"DELETE FROM audit_logs WHERE id = {log_id};",
    ]
    res_delete = subprocess.run(delete_cmd, capture_output=True, text=True)
    assert res_delete.returncode != 0
    assert "Operação proibida" in res_delete.stderr

    # 5. Tentar esvaziamento (TRUNCATE) com usuário admin no banco -> deve falhar
    truncate_cmd = [
        "docker", "compose", "exec", "-T", "log-db",
        "psql", "-U", "log_admin", "-d", "segurasaude_logs",
        "-c", "TRUNCATE TABLE audit_logs;",
    ]
    res_truncate = subprocess.run(truncate_cmd, capture_output=True, text=True)
    assert res_truncate.returncode != 0
    assert "Operação proibida" in res_truncate.stderr

    # 6. Critério de Aceite: Verificar integridade (100% dos dados mantidos intactos)
    final_count = int(subprocess.run(count_cmd, capture_output=True, text=True, check=True).stdout.strip())
    assert final_count == initial_count + 1, "A contagem de registros foi violada após tentativas de exclusão!"

    # Conferir se o registro inserido permaneceu inalterado
    check_record_cmd = [
        "docker", "compose", "exec", "-T", "log-db",
        "psql", "-U", "log_admin", "-d", "segurasaude_logs", "-t", "-A",
        "-c", f"SELECT action FROM audit_logs WHERE id = {log_id};",
    ]
    record_action = subprocess.run(check_record_cmd, capture_output=True, text=True, check=True).stdout.strip()
    assert record_action == "TESTE_IMUTABILIDADE_CQ01", f"Registro foi corrompido! Valor: {record_action}"

