"""
Testes de integração – Motor e Endpoints da Matriz de Risco (RF001, DT03).

Critérios de aceite:
  1. Calcular o nível de risco (Baixo, Médio, Alto, Crítico) cruzando
     sensibilidade do dado, ausência de criptografia e atores com acesso.
  2. Gerar a ação recomendada correspondente (Criptografar, Remover acesso, Manter log de acesso).
  3. Persistir a matriz calculada para consulta via GET /matriz/lotes/{lote_id}.
  4. Disparar registro automático no Serviço de Log.
"""

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
    # Inicializa os serviços necessários para o teste
    try:
        subprocess.run(
            [
                "docker", "compose", "up", "-d", "--wait",
                "metadados-db", "log-db", "log-service", "gateway-1",
            ],
            check=True,
            capture_output=True,
            text=True
    )
    except subprocess.CalledProcessError as e:
        print("ERRO NO DOCKER!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("STDERR:", e.stderr)
        print("STDOUT:", e.stdout)
        raise

    # Aguarda o gateway responder
    for _ in range(15):
        try:
            resp = requests.get(f"{API_URL}/health", timeout=2)
            if resp.status_code == 200:
                break
        except requests.ConnectionError:
            pass
        time.sleep(2)

    yield

    # Limpeza para evitar conflito com outros testes de infraestrutura
    subprocess.run(
        ["docker", "compose", "down", "-v", "--remove-orphans"],
        check=False,
    )


class TestMatrizRiscoEndpoints:

    def test_calcular_lote_inexistente_retorna_404(self):
        """Calcular matriz para lote inexistente deve retornar HTTP 404."""
        resp = requests.post(
            f"{API_URL}/matriz/lotes/00000000-0000-0000-0000-000000000000/calcular",
            timeout=5,
        )
        assert resp.status_code == 404
        assert "Lote não encontrado" in resp.json()["detail"]

    def test_obter_matriz_lote_inexistente_retorna_404(self):
        """Consultar matriz para lote inexistente deve retornar HTTP 404."""
        resp = requests.get(
            f"{API_URL}/matriz/lotes/00000000-0000-0000-0000-000000000000",
            timeout=5,
        )
        assert resp.status_code == 404
        assert "Lote não encontrado" in resp.json()["detail"]

    def test_obter_matriz_antes_de_calcular_retorna_404(self):
        """Lote criado sem metadados (metadados: []) não gera matriz na ingestão e deve retornar 404 ao consultar matriz."""
        lote_resp = requests.post(
            f"{API_URL}/metadados/lotes",
            json={
                "nome_lote": "Lote Sem Matriz Ainda",
                "base_legal": "Consentimento",
                "metadados": [],
            },
            timeout=5,
        )
        assert lote_resp.status_code == 201
        lote_id = lote_resp.json()["id"]

        resp = requests.get(f"{API_URL}/matriz/lotes/{lote_id}", timeout=5)
        assert resp.status_code == 404
        assert "ainda não calculada" in resp.json()["detail"]

    def test_matriz_calculada_automaticamente_na_ingestao(self):
        """Ao criar um lote com metadados (total > 0), a matriz deve ser calculada e disponibilizada em GET sem chamar /calcular."""
        payload = {
            "nome_lote": "Lote Calculo Automatico Ingestao",
            "base_legal": "Execucao de Contrato",
            "analista_responsavel": "analista_auto",
            "metadados": [
                {
                    "origem": "tabela_contratos",
                    "temporalidade": "5 anos",
                    "crm_responsavel": "CRM-SE-11223",
                    "tipo_dado": "Nome",
                    "categoria": "Identificador",
                    "base_legal": "Execucao de Contrato",
                    "criptografado": True,
                    "atores_com_acesso": ["administrador"],
                }
            ],
        }
        lote_resp = requests.post(f"{API_URL}/metadados/lotes", json=payload, timeout=5)
        assert lote_resp.status_code == 201
        lote_id = lote_resp.json()["id"]

        # GET direto na matriz do lote sem ter acionado POST /matriz/lotes/{id}/calcular
        resp = requests.get(f"{API_URL}/matriz/lotes/{lote_id}", timeout=5)
        assert resp.status_code == 200
        matriz = resp.json()
        assert matriz["id_lote"] == lote_id
        assert matriz["nivel_risco"] == 0

    def test_calcular_e_obter_matriz_risco_critico(self):
        """
        Lote com dado sensível de saúde (CID-10), sem criptografia e múltiplos atores (incluindo terceiros)
        deve resultar em Nível CRÍTICO (3) com ações correspondentes.
        """
        # 1. Cria o lote
        payload = {
            "nome_lote": "Lote Prontuários UTI - Alta Exposição",
            "base_legal": "Tutela da Saúde",
            "analista_responsavel": "analista_seguranca",
            "metadados": [
                {
                    "origem": "tabela_prontuario_uti",
                    "temporalidade": "20 anos",
                    "crm_responsavel": "CRM-SE-99881",
                    "tipo_dado": "CID-10_Diagnostico",
                    "categoria": "Sensível",
                    "base_legal": "Tutela da Saúde",
                    "criptografado": False,
                    "atores_com_acesso": ["medico", "enfermeiro", "terceiro_pesquisa", "externo"],
                }
            ],
        }
        lote_resp = requests.post(f"{API_URL}/metadados/lotes", json=payload, timeout=5)
        assert lote_resp.status_code == 201
        lote_id = lote_resp.json()["id"]

        # 2. Executa o cálculo síncrono da matriz (POST /matriz/lotes/{id}/calcular)
        calc_resp = requests.post(f"{API_URL}/matriz/lotes/{lote_id}/calcular", timeout=5)
        assert calc_resp.status_code == 200
        matriz = calc_resp.json()

        assert matriz["id_lote"] == lote_id
        assert matriz["nivel_risco"] == 3  # CRÍTICO
        assert "URGENTE: Criptografar" in matriz["recomendacao_acao"]
        assert "Revogar o acesso" in matriz["recomendacao_acao"]
        assert "Manter log de acesso" in matriz["recomendacao_acao"]
        assert len(matriz["detalhes"]) == 1
        assert matriz["detalhes"][0]["nivel_risco"] == 3
        assert matriz["detalhes"][0]["sensibilidade"] == "SENSÍVEL_SAÚDE"

        # 3. Consulta a matriz persistida (GET /matriz/lotes/{id})
        get_resp = requests.get(f"{API_URL}/matriz/lotes/{lote_id}", timeout=5)
        assert get_resp.status_code == 200
        matriz_get = get_resp.json()
        assert matriz_get["id"] == matriz["id"]
        assert matriz_get["nivel_risco"] == 3
        assert matriz_get["recomendacao_acao"] == matriz["recomendacao_acao"]

        # 4. Verifica registro de log no Serviço de Log
        time.sleep(1)
        log_resp = requests.get(f"{LOG_API_URL}/logs/system?limit=20", timeout=5)
        assert log_resp.status_code == 200
        logs = log_resp.json()
        assert any(
            lote_id in str(log.get("context", {})) and "Matriz de risco calculada" in log.get("message", "")
            for log in logs
        ), f"Log de cálculo da matriz não encontrado para o lote {lote_id}"

    def test_calcular_e_obter_matriz_risco_baixo(self):
        """
        Lote com dados PII criptografados e acesso restrito deve resultar em Nível BAIXO (0).
        """
        payload = {
            "nome_lote": "Lote Pacientes Criptografados",
            "base_legal": "Obrigação Legal",
            "analista_responsavel": "dpo_hospital",
            "metadados": [
                {
                    "origem": "tabela_pacientes_segura",
                    "temporalidade": "5 anos",
                    "crm_responsavel": "CRM-SE-12345",
                    "tipo_dado": "CPF",
                    "categoria": "Identificador",
                    "base_legal": "Obrigação Legal",
                    "criptografado": True,
                    "atores_com_acesso": ["medico_responsavel"],
                }
            ],
        }
        lote_resp = requests.post(f"{API_URL}/metadados/lotes", json=payload, timeout=5)
        assert lote_resp.status_code == 201
        lote_id = lote_resp.json()["id"]

        calc_resp = requests.post(f"{API_URL}/matriz/lotes/{lote_id}/calcular", timeout=5)
        assert calc_resp.status_code == 200
        matriz = calc_resp.json()

        assert matriz["nivel_risco"] == 0  # BAIXO
        assert "Manter log de acesso ativo" in matriz["recomendacao_acao"]
        assert len(matriz["detalhes"]) == 1
        assert matriz["detalhes"][0]["nivel_risco"] == 0
