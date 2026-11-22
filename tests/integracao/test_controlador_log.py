"""
Testes de integração – Consulta de logs e registro de AuditLog pelo gateway (RF005).

Critérios de aceite (feat-6):
  1. Listagem somente leitura dos logs registrados, via gateway.
  2. Registro de AuditLog exigindo o campo motivo.
"""

import os
import subprocess
import time

import pytest
import requests

API_URL = os.getenv("API_URL", "http://localhost:8082")

AUDIT_VALIDO = {
    "actor_id": "dev_feat6",
    "actor_role": "DESENVOLVEDOR",
    "action": "REVISAO_ACESSO",
    "resource": "lote_sintetico_feat6",
    "motivo": "Auditoria LGPD de acesso ao lote sintético",
}


@pytest.fixture(scope="module", autouse=True)
def ensure_services_running():
    subprocess.run(
        [
            "docker", "compose", "up", "-d", "--wait",
            "metadados-db", "log-db", "log-service", "gateway-1",
        ],
        check=True,
    )
    for _ in range(12):
        try:
            if requests.get(f"{API_URL}/health", timeout=2).status_code == 200:
                break
        except requests.ConnectionError:
            pass
        time.sleep(2)

    yield

    subprocess.run(
        ["docker", "compose", "down", "-v", "--remove-orphans"],
        check=False,
    )


# ── Listagem somente leitura via gateway ───────────────────────────────
class TestListagemLogs:

    def test_listar_audit_logs_pelo_gateway(self):
        resp = requests.get(f"{API_URL}/logs/audit?limit=10", timeout=5)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_listar_logs_sistema_pelo_gateway(self):
        resp = requests.get(f"{API_URL}/logs/system?limit=10", timeout=5)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_limite_fora_da_faixa_retorna_422(self):
        assert requests.get(f"{API_URL}/logs/audit?limit=0", timeout=5).status_code == 422
        assert requests.get(f"{API_URL}/logs/audit?limit=501", timeout=5).status_code == 422

    def test_gateway_nao_expoe_alteracao_nem_exclusao(self):
        for metodo in (requests.put, requests.patch):
            assert metodo(f"{API_URL}/logs/audit/1", json={}, timeout=5).status_code in (404, 405)
        assert requests.delete(f"{API_URL}/logs/audit/1", timeout=5).status_code in (404, 405)
        assert requests.delete(f"{API_URL}/logs/audit", timeout=5).status_code == 405


# ── Registro de AuditLog com motivo obrigatório ────────────────────────
class TestRegistroAuditLog:

    def test_sem_motivo_retorna_422(self):
        payload = {k: v for k, v in AUDIT_VALIDO.items() if k != "motivo"}
        resp = requests.post(f"{API_URL}/logs/audit", json=payload, timeout=5)
        assert resp.status_code == 422

    def test_motivo_so_com_espacos_retorna_422(self):
        payload = {**AUDIT_VALIDO, "motivo": "   "}
        resp = requests.post(f"{API_URL}/logs/audit", json=payload, timeout=5)
        assert resp.status_code == 422

    def test_perfil_invalido_retorna_422(self):
        payload = {**AUDIT_VALIDO, "actor_role": "ADMIN"}
        resp = requests.post(f"{API_URL}/logs/audit", json=payload, timeout=5)
        assert resp.status_code == 422

    def test_registro_com_motivo_aparece_na_listagem(self):
        resp = requests.post(f"{API_URL}/logs/audit", json=AUDIT_VALIDO, timeout=5)
        assert resp.status_code == 201
        criado = resp.json()

        lista = requests.get(f"{API_URL}/logs/audit?limit=20", timeout=5).json()
        registro = next(item for item in lista if item["event_id"] == criado["event_id"])
        assert registro["actor_id"] == "dev_feat6"
        assert registro["status"] == "SUCCESS"
        assert registro["details"]["motivo"] == AUDIT_VALIDO["motivo"]
