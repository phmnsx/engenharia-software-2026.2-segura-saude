"""
Testes de integração – Endpoint de ingestão de metadados (RF004, RN01).

Critérios de aceite:
  1. Rejeitar com HTTP 400 qualquer lote sem baseLegal preenchida (RN01).
  2. Persistir lote válido no banco de dados principal.
  3. Disparar registro automático de ação no Serviço de Log (LogSistema).
"""

import json
import os
import subprocess
import time

import pytest
import requests

API_URL = os.getenv("API_URL", "http://localhost:8082")
LOG_API_URL = os.getenv("LOG_API_URL", "http://localhost:8005")


@pytest.fixture(scope="module", autouse=True)
def ensure_services_running():
    subprocess.run(
        ["docker", "compose", "down", "-v", "--remove-orphans"],
        check=False,
    )
    subprocess.run(
        [
            "docker", "compose", "up", "-d", "--wait",
            "metadados-db", "log-db", "log-service", "gateway-1",
        ],
        check=True,
    )
    # Aguardar gateway estar respondendo
    for _ in range(12):
        try:
            resp = requests.get(f"{API_URL}/health", timeout=2)
            if resp.status_code == 200:
                break
        except requests.ConnectionError:
            pass
        time.sleep(2)

    yield

    # Derruba os containers para não colidir com outros testes (ex: test_cluster)
    subprocess.run(
        ["docker", "compose", "down", "-v", "--remove-orphans"],
        check=False,
    )


# ── RN01: Rejeitar lote sem base_legal (HTTP 400) ──────────────────────
class TestRN01RejeicaoSemBaseLegal:

    def test_json_sem_base_legal_retorna_422(self):
        """Payload JSON sem campo base_legal deve ser rejeitado."""
        resp = requests.post(
            f"{API_URL}/metadados/lotes",
            json={"nome_lote": "Lote Sem Base Legal"},
            timeout=5,
        )
        assert resp.status_code == 422

    def test_json_base_legal_vazia_retorna_422(self):
        """Payload JSON com base_legal vazia deve ser rejeitado."""
        resp = requests.post(
            f"{API_URL}/metadados/lotes",
            json={"nome_lote": "Lote Vazio", "base_legal": ""},
            timeout=5,
        )
        assert resp.status_code == 422

    def test_form_sem_base_legal_retorna_422(self):
        """Formulário sem campo base_legal deve ser rejeitado."""
        resp = requests.post(
            f"{API_URL}/metadados/lotes/form",
            data={"nome_lote": "Lote Formulário Sem BL"},
            timeout=5,
        )
        assert resp.status_code == 422

    def test_form_base_legal_vazia_retorna_400(self):
        """Formulário com base_legal vazia (apenas espaços) deve retornar 400."""
        resp = requests.post(
            f"{API_URL}/metadados/lotes/form",
            data={"nome_lote": "Lote Formulário Vazio", "base_legal": "   "},
            timeout=5,
        )
        assert resp.status_code == 400
        assert "obrigatório" in resp.json()["detail"].lower() or "RN01" in resp.json()["detail"]


# ── RF004: Persistir lote válido via JSON ───────────────────────────────
class TestRF004IngestaoJSON:

    def test_criar_lote_json_com_metadados(self):
        """Lote válido via JSON deve ser persistido (HTTP 201)."""
        payload = {
            "nome_lote": "Lote Sintético RF004-JSON",
            "base_legal": "Consentimento",
            "analista_responsavel": "analista_rf004",
            "metadados": [
                {
                    "origem": "tabela_pacientes",
                    "temporalidade": "5 anos",
                    "crm_responsavel": "CRM-SE-12345",
                    "tipo_dado": "VARCHAR",
                    "categoria": "Sensível",
                    "base_legal": "Consentimento",
                    "criptografado": True,
                    "atores_com_acesso": ["medico", "analista"],
                },
                {
                    "origem": "tabela_exames",
                    "temporalidade": "10 anos",
                    "crm_responsavel": "CRM-SE-67890",
                },
            ],
        }
        resp = requests.post(f"{API_URL}/metadados/lotes", json=payload, timeout=5)
        assert resp.status_code == 201
        body = resp.json()
        assert body["nome_lote"] == "Lote Sintético RF004-JSON"
        assert body["base_legal"] == "Consentimento"
        assert body["total_metadados"] == 2

        # Verificar persistência consultando o lote
        lote_id = body["id"]
        get_resp = requests.get(f"{API_URL}/metadados/lotes/{lote_id}", timeout=5)
        assert get_resp.status_code == 200
        lote = get_resp.json()
        assert len(lote["metadados"]) == 2
        assert lote["metadados"][0]["criptografado"] is True

    def test_criar_lote_json_sem_metadados(self):
        """Lote válido sem metadados (apenas cabeçalho) deve ser aceito."""
        payload = {
            "nome_lote": "Lote Vazio RF004",
            "base_legal": "Legítimo Interesse",
        }
        resp = requests.post(f"{API_URL}/metadados/lotes", json=payload, timeout=5)
        assert resp.status_code == 201
        assert resp.json()["total_metadados"] == 0


# ── RF004: Persistir lote válido via Formulário ─────────────────────────
class TestRF004IngestaoFormulario:

    def test_criar_lote_formulario_com_metadados(self):
        """Lote via formulário com metadados_json deve ser persistido."""
        metadados = [
            {
                "origem": "tabela_prontuarios",
                "temporalidade": "20 anos",
                "crm_responsavel": "CRM-SE-55555",
            }
        ]
        resp = requests.post(
            f"{API_URL}/metadados/lotes/form",
            data={
                "nome_lote": "Lote Formulário RF004",
                "base_legal": "Tutela da Saúde",
                "analista_responsavel": "analista_form",
                "metadados_json": json.dumps(metadados),
            },
            timeout=5,
        )
        assert resp.status_code == 201
        assert resp.json()["total_metadados"] == 1

    def test_criar_lote_formulario_metadados_json_invalido(self):
        """Formulário com metadados_json inválido deve retornar 400."""
        resp = requests.post(
            f"{API_URL}/metadados/lotes/form",
            data={
                "nome_lote": "Lote JSON Inválido",
                "base_legal": "Consentimento",
                "metadados_json": "{ isso não é json }",
            },
            timeout=5,
        )
        assert resp.status_code == 400
        assert "JSON inválido" in resp.json()["detail"]


# ── Listagem de lotes ───────────────────────────────────────────────────
class TestListagemLotes:

    def test_listar_lotes_retorna_cadastrados(self):
        """GET /metadados/lotes deve retornar os lotes existentes."""
        resp = requests.get(f"{API_URL}/metadados/lotes", timeout=5)
        assert resp.status_code == 200
        lotes = resp.json()
        assert isinstance(lotes, list)
        assert len(lotes) >= 1


# ── Disparo automático de LogSistema ────────────────────────────────────
class TestLogSistemaAutomatico:

    def test_log_sistema_registrado_apos_criacao(self):
        """Após criar lote, deve existir um registro no Serviço de Log (LogSistema)."""
        payload = {
            "nome_lote": "Lote Para Log RF004",
            "base_legal": "Consentimento",
            "analista_responsavel": "analista_log_test",
        }
        resp = requests.post(f"{API_URL}/metadados/lotes", json=payload, timeout=5)
        assert resp.status_code == 201
        lote_id = resp.json()["id"]

        # Aguardar propagação do log
        time.sleep(1)

        log_resp = requests.get(f"{LOG_API_URL}/logs/system?limit=20", timeout=5)
        assert log_resp.status_code == 200
        logs = log_resp.json()
        assert any(
            lote_id in str(log.get("context", {})) or "Lote Para Log RF004" in log.get("message", "")
            for log in logs
        ), f"Log de sistema não encontrado para lote {lote_id}"
