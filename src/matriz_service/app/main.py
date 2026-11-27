import json
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query

from app.db import get_connection
from app.servico_matriz import calcular_e_salvar
from common.log_client import send_system_log
from common.rabbitmqconfig.consumer import RabbitMQConsumer

logger = logging.getLogger(__name__)
consumer = RabbitMQConsumer()


async def _processar_tarefa_matriz(payload: dict):
    dados = payload["data"]
    lote_id = dados["id_lote"]
    matriz_id = dados.get("id_matriz")
    resultado = calcular_e_salvar(lote_id, matriz_id=matriz_id)
    if not resultado:
        logger.warning("[MatrizService] Lote %s não encontrado ao processar cálculo.", lote_id)


async def _processar_ingestao_metadados(payload: dict):
    dados = payload["data"]
    lote_id = dados["id"]
    metadados = dados.get("metadados", [])

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO lotes_metadados (id, nome_lote, base_legal, analista_responsavel)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
            """,
            (
                lote_id,
                dados["nome_lote"],
                dados["base_legal"],
                dados.get("analista_responsavel"),
            ),
        )

        for m in metadados:
            cur.execute(
                """
                INSERT INTO metadados
                    (id, id_lote, origem, temporalidade, crm_responsavel,
                     tipo_dado, categoria, base_legal, criptografado, atores_com_acesso)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb);
                """,
                (
                    str(uuid4()),
                    lote_id,
                    m["origem"],
                    m["temporalidade"],
                    m.get("crm_responsavel"),
                    m["tipo_dado"],
                    m["categoria"],
                    m["base_legal"],
                    m["criptografado"],
                    json.dumps(m.get("atores_com_acesso", [])),
                ),
            )

        conn.commit()

    total = len(metadados)
    send_system_log(
        service_name="matriz-service",
        level="INFO",
        message=f"Lote de metadados '{dados['nome_lote']}' criado com {total} registro(s).",
        context={
            "lote_id": lote_id,
            "base_legal": dados["base_legal"],
            "analista": dados.get("analista_responsavel"),
            "total_metadados": total,
        },
    )

    if total > 0:
        try:
            calcular_e_salvar(lote_id)
        except Exception as exc:
            logger.error("Falha ao calcular matriz para o lote %s: %s", lote_id, exc, exc_info=True)
            send_system_log(
                service_name="matriz-service",
                level="ERROR",
                message=f"Falha ao calcular matriz automaticamente para o lote '{dados['nome_lote']}': {exc}",
                context={"lote_id": lote_id, "erro": str(exc)},
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await consumer.iniciar_consumo_matriz(_processar_tarefa_matriz)
    await consumer.iniciar_consumo_metadados(_processar_ingestao_metadados)
    yield
    await consumer.conn_manager.close()


app = FastAPI(title="SeguraSaúde - Serviço de Matriz e Metadados", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/matriz/lotes/{lote_id}")
def obter_matriz_risco(lote_id: str):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM lotes_metadados WHERE id = %s;", (lote_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Lote não encontrado.")

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


@app.get("/metadados/lotes")
def listar_lotes(limit: int = Query(50, ge=1, le=500)):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT l.*, COUNT(m.id) AS total_metadados
            FROM lotes_metadados l
            LEFT JOIN metadados m ON m.id_lote = l.id
            GROUP BY l.id
            ORDER BY l.data_criacao DESC
            LIMIT %s;
            """,
            (limit,),
        )
        return cur.fetchall()


@app.get("/metadados/lotes/{lote_id}")
def obter_lote(lote_id: str):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM lotes_metadados WHERE id = %s;", (lote_id,))
        lote = cur.fetchone()
        if not lote:
            raise HTTPException(status_code=404, detail="Lote não encontrado.")

        cur.execute("SELECT * FROM metadados WHERE id_lote = %s;", (lote_id,))
        lote["metadados"] = cur.fetchall()
        return lote
