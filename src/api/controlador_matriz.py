"""
ControladorMatriz – Endpoints para cálculo e consulta da Matriz de Risco (RF001, DT03).

O gateway encaminha solicitações de cálculo (POST) via RabbitMQ para o
Serviço de Matriz e consultas (GET) via HTTP.
"""

import json
import os
import urllib.error
import urllib.request
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from api.schemas import MatrizDeRiscoOut
from common.rabbitmqconfig.publisher import RabbitMQPublisher

MATRIZ_SERVICE_URL = os.getenv("MATRIZ_SERVICE_URL", "http://matriz-service:8000")
TIMEOUT_SEGUNDOS = 5.0

router = APIRouter(prefix="/matriz", tags=["Matriz de Risco"])
publisher = RabbitMQPublisher()


def _chamar_servico_matriz(metodo: str, caminho: str):
    req = urllib.request.Request(
        f"{MATRIZ_SERVICE_URL}{caminho}",
        headers={"Content-Type": "application/json"},
        method=metodo,
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEGUNDOS) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            detalhe = "Recurso não encontrado."
            try:
                detalhe = json.loads(e.read().decode("utf-8")).get("detail", detalhe)
            except Exception:
                pass
            raise HTTPException(status_code=404, detail=detalhe)
        raise HTTPException(
            status_code=502,
            detail="O Serviço de Matriz recusou a requisição.",
        )
    except (urllib.error.URLError, TimeoutError):
        raise HTTPException(
            status_code=503,
            detail="Serviço de Matriz indisponível no momento.",
        )


# ── POST /matriz/lotes/{lote_id}/calcular (assíncrono via RabbitMQ) ────
@router.post("/lotes/{lote_id}/calcular", status_code=202)
async def calcular_matriz_risco(lote_id: str):
    """
    Solicita o cálculo assíncrono da Matriz de Risco publicando na fila do RabbitMQ (ASR06).
    """
    id_matriz = str(uuid4())
    try:
        await publisher.publicar_tarefa_matriz(
            id_lote=lote_id,
            id_matriz=id_matriz,
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Mensageria indisponível. O cálculo não foi enfileirado; tente novamente.",
        )
    return {
        "id_matriz": id_matriz,
        "id_lote": lote_id,
        "status": "PENDENTE",
        "mensagem": "Cálculo da matriz de risco enfileirado.",
    }


# ── GET /matriz/lotes/{lote_id} (somente leitura via HTTP) ─────────────
@router.get("/lotes/{lote_id}", response_model=MatrizDeRiscoOut)
def obter_matriz_risco(lote_id: str):
    """
    Retorna a Matriz de Risco mais recente calculada para o lote informado.
    """
    return _chamar_servico_matriz("GET", f"/matriz/lotes/{lote_id}")
