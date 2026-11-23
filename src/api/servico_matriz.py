"""
Serviço de cálculo e persistência da Matriz de Risco (RF001, DT03).
Pode ser acionado tanto via endpoint da API quanto automaticamente durante a ingestão de lotes.
"""

import json
from uuid import uuid4
from typing import Optional

from api.db import get_connection
from api.motor_risco import calcular_matriz_lote
from common.log_client import send_system_log


def calcular_e_salvar(lote_id: str) -> Optional[dict]:
    """
    Executa o cálculo síncrono da Matriz de Risco para um lote de metadados (RF001, DT03)
    e persiste o resultado na base de dados, emitindo log de auditoria.

    Retorna o dicionário da matriz calculada ou None se o lote não existir.
    """
    with get_connection() as conn, conn.cursor() as cur:
        # 1. Verifica se o lote de metadados existe
        cur.execute("SELECT * FROM lotes_metadados WHERE id = %s;", (lote_id,))
        lote = cur.fetchone()
        if not lote:
            return None

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
