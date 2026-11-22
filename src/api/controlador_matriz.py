"""
ControladorMatriz – Endpoints para cálculo e consulta da Matriz de Risco (RF001, DT03).

Disponibiliza o motor de cálculo síncrono da Matriz de Risco baseado na LGPD (DT03, DT02)
e integra com o Serviço de Log para auditoria de cada cálculo efetuado.
"""

import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from api.db import get_connection
from api.schemas import MatrizDeRiscoOut
from api.servico_matriz import calcular_e_salvar

router = APIRouter(prefix="/matriz", tags=["Matriz de Risco"])


# ── POST /matriz/lotes/{lote_id}/calcular ──────────────────────────────
@router.post("/lotes/{lote_id}/calcular", response_model=MatrizDeRiscoOut, status_code=200)
def calcular_matriz_risco(lote_id: str):
    """
    Executa o cálculo síncrono da Matriz de Risco para um lote de metadados (RF001, DT03).
    Cruza sensibilidade do dado, ausência de criptografia e superfície de acesso de atores,
    gerando o nível consolidado e a ação recomendada correspondente.
    """
    matriz = calcular_e_salvar(lote_id)
    if not matriz:
        raise HTTPException(status_code=404, detail="Lote não encontrado.")
    return matriz


# ── GET /matriz/lotes/{lote_id} ─────────────────────────────────────────
@router.get("/lotes/{lote_id}", response_model=MatrizDeRiscoOut)
def obter_matriz_risco(lote_id: str):
    """
    Retorna a Matriz de Risco mais recente calculada para o lote informado.
    """
    with get_connection() as conn, conn.cursor() as cur:
        # Verifica se o lote existe
        cur.execute("SELECT id FROM lotes_metadados WHERE id = %s;", (lote_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Lote não encontrado.")

        # Busca a matriz mais recente do lote
        cur.execute(
            """
            SELECT id, id_lote, nivel_risco, recomendacao_acao, detalhes, data_hora
            FROM matrizes_risco
            WHERE id_lote = %s
            ORDER BY data_hora DESC
            LIMIT 1;
            """,
            (lote_id,),
        )
        matriz = cur.fetchone()
        if not matriz:
            raise HTTPException(
                status_code=404,
                detail="Matriz de risco ainda não calculada para este lote.",
            )

        if isinstance(matriz.get("detalhes"), str):
            matriz["detalhes"] = json.loads(matriz["detalhes"])

        return matriz
