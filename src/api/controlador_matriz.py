"""
ControladorMatriz – Endpoints para cálculo e consulta da Matriz de Risco (RF001, DT03).

Disponibiliza o motor de cálculo síncrono da Matriz de Risco baseado na LGPD (DT03, DT02)
e integra com o Serviço de Log para auditoria de cada cálculo efetuado.
"""

import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from api.db import get_connection
from api.motor_risco import calcular_matriz_lote
from api.schemas import MatrizDeRiscoOut
from common.log_client import send_system_log

router = APIRouter(prefix="/matriz", tags=["Matriz de Risco"])


# ── POST /matriz/lotes/{lote_id}/calcular ──────────────────────────────
@router.post("/lotes/{lote_id}/calcular", response_model=MatrizDeRiscoOut, status_code=200)
def calcular_matriz_risco(lote_id: str):
    """
    Executa o cálculo síncrono da Matriz de Risco para um lote de metadados (RF001, DT03).
    Cruza sensibilidade do dado, ausência de criptografia e superfície de acesso de atores,
    gerando o nível consolidado e a ação recomendada correspondente.
    """
    with get_connection() as conn, conn.cursor() as cur:
        # 1. Verifica se o lote de metadados existe
        cur.execute("SELECT * FROM lotes_metadados WHERE id = %s;", (lote_id,))
        lote = cur.fetchone()
        if not lote:
            raise HTTPException(status_code=404, detail="Lote não encontrado.")

        # 2. Busca todos os metadados associados ao lote
        cur.execute("SELECT * FROM metadados WHERE id_lote = %s;", (lote_id,))
        metadados_rows = cur.fetchall()

        # Desserializa atores_com_acesso se necessário
        metadados_processados = []
        for m in metadados_rows:
            m_dict = dict(m)
            if isinstance(m_dict.get("atores_com_acesso"), str):
                try:
                    m_dict["atores_com_acesso"] = json.loads(m_dict["atores_com_acesso"])
                except json.JSONDecodeError:
                    m_dict["atores_com_acesso"] = []
            metadados_processados.append(m_dict)

        # 3. Executa o motor síncrono de cálculo LGPD (DT03)
        nivel_risco, recomendacao, detalhes = calcular_matriz_lote(metadados_processados)

        # 4. Persiste o resultado da matriz de risco
        matriz_id = str(uuid4())
        cur.execute(
            """
            INSERT INTO matrizes_risco (id, id_lote, nivel_risco, recomendacao_acao, detalhes)
            VALUES (%s, %s, %s, %s, %s::jsonb)
            RETURNING id, id_lote, nivel_risco, recomendacao_acao, detalhes, data_hora;
            """,
            (
                matriz_id,
                lote_id,
                nivel_risco,
                recomendacao,
                json.dumps(detalhes),
            ),
        )
        matriz_row = cur.fetchone()
        conn.commit()

    # Desserializa detalhes se retornado como string
    if isinstance(matriz_row.get("detalhes"), str):
        matriz_row["detalhes"] = json.loads(matriz_row["detalhes"])

    # 5. Registro automático de auditoria no Serviço de Log
    send_system_log(
        service_name="api-gateway",
        level="INFO",
        message=f"Matriz de risco calculada para o lote '{lote['nome_lote']}' (Nível: {nivel_risco}).",
        context={
            "lote_id": str(lote_id),
            "matriz_id": str(matriz_id),
            "nivel_risco": int(nivel_risco),
            "recomendacao_acao": recomendacao,
            "total_metadados": len(metadados_processados),
        },
    )

    return matriz_row


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
