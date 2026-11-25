"""
Testes de integração – Padronização das respostas HTTP da API (fix-1).

Critérios de aceite:
  1. UUID com formato inválido retorna 422, não 500.
  2. Recálculo de lote sem metadados retorna 422.
  3. Endpoints de cadastro retornam 201 Created.
"""

import os
import subprocess
import time

import pytest
import requests

API_URL = os.getenv("API_URL", "http://localhost:8082")
UUID_INEXISTENTE = "00000000-0000-0000-0000-000000000000"
IDS_INVALIDOS = ["nao-e-uuid", "123", "1 OR 1=1"]

METADADO = {
    "origem": "prontuario.paciente",
    "temporalidade": "20 anos",
    "crm_responsavel": "CRM-SE-1234",
    "tipo_dado": "CPF",
    "categoria": "Identificador",
    "criptografado": False,
    "atores_com_acesso": ["medico"],
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
    for _ in range(15):
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


def _criar_lote(metadados):
    resp = requests.post(
        f"{API_URL}/metadados/lotes",
        json={"nome_lote": "Lote fix-1", "base_legal": "Art. 11, II, f", "metadados": metadados},
        timeout=5,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ── 1. UUID inválido → 422 ──────────────────────────────────────────────
class TestUuidInvalido:

    @pytest.mark.parametrize("lote_id", IDS_INVALIDOS)
    def test_obter_lote_com_uuid_invalido_retorna_422(self, lote_id):
        resp = requests.get(f"{API_URL}/metadados/lotes/{lote_id}", timeout=5)
        assert resp.status_code == 422

    @pytest.mark.parametrize("lote_id", IDS_INVALIDOS)
    def test_obter_matriz_com_uuid_invalido_retorna_422(self, lote_id):
        resp = requests.get(f"{API_URL}/matriz/lotes/{lote_id}", timeout=5)
        assert resp.status_code == 422

    @pytest.mark.parametrize("lote_id", IDS_INVALIDOS)
    def test_calcular_matriz_com_uuid_invalido_retorna_422(self, lote_id):
        resp = requests.post(f"{API_URL}/matriz/lotes/{lote_id}/calcular", timeout=5)
        assert resp.status_code == 422

    def test_uuid_valido_inexistente_continua_404(self):
        assert requests.get(f"{API_URL}/metadados/lotes/{UUID_INEXISTENTE}", timeout=5).status_code == 404
        assert requests.get(f"{API_URL}/matriz/lotes/{UUID_INEXISTENTE}", timeout=5).status_code == 404
        resp = requests.post(f"{API_URL}/matriz/lotes/{UUID_INEXISTENTE}/calcular", timeout=5)
        assert resp.status_code == 404


# ── 2. Recálculo de lote vazio → 422 ────────────────────────────────────
class TestLoteVazio:

    def test_calcular_lote_sem_metadados_retorna_422(self):
        lote_id = _criar_lote([])
        resp = requests.post(f"{API_URL}/matriz/lotes/{lote_id}/calcular", timeout=5)
        assert resp.status_code == 422
        assert "sem metadados" in resp.json()["detail"]

    def test_lote_sem_metadados_nao_grava_matriz(self):
        lote_id = _criar_lote([])
        requests.post(f"{API_URL}/matriz/lotes/{lote_id}/calcular", timeout=5)
        resp = requests.get(f"{API_URL}/matriz/lotes/{lote_id}", timeout=5)
        assert resp.status_code == 404

    def test_calcular_lote_com_metadados_continua_200(self):
        lote_id = _criar_lote([METADADO])
        resp = requests.post(f"{API_URL}/matriz/lotes/{lote_id}/calcular", timeout=5)
        assert resp.status_code == 200


# ── 3. Cadastro → 201 Created ───────────────────────────────────────────
class TestCadastroRetorna201:

    def test_cadastro_lote_json_retorna_201(self):
        _criar_lote([METADADO])

    def test_cadastro_lote_formulario_retorna_201(self):
        resp = requests.post(
            f"{API_URL}/metadados/lotes/form",
            data={"nome_lote": "Lote form fix-1", "base_legal": "Art. 11, II, f"},
            timeout=5,
        )
        assert resp.status_code == 201

    def test_cadastro_audit_log_retorna_201(self):
        resp = requests.post(
            f"{API_URL}/logs/audit",
            json={
                "actor_id": "dev_fix1",
                "actor_role": "DESENVOLVEDOR",
                "action": "REVISAO_ACESSO",
                "resource": "lote_fix1",
                "motivo": "Validação do status 201 no cadastro",
            },
            timeout=5,
        )
        assert resp.status_code == 201
