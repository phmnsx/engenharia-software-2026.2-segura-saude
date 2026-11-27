import asyncio
import json
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query

from common.outbox.db import SessionLocal
from app.db import get_connection
from app.servico_matriz import calcular_e_salvar
from common.rabbitmqconfig.consumer import RabbitMQConsumer
from common.rabbitmqconfig.publisher import RabbitMQPublisher

logger = logging.getLogger(__name__)
consumer = RabbitMQConsumer()
publisher = RabbitMQPublisher()

async def _processar_tarefa_matriz(payload: dict):
    id_msg = payload.get("id_msg")
    dados = payload.get("data", {})
    lote_id = dados.get("id_lote")
    matriz_id = dados.get("id_matriz")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM matrizes_risco WHERE event_id = %s;", (id_msg,))
        if cur.fetchone():
            logger.info(f"[Idempotência] Cálculo {id_msg} já realizado. Ignorando.")
            return
        try:
            resultado = calcular_e_salvar(lote_id, matriz_id=matriz_id, event_id=id_msg, cursor=cur)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise


async def _processar_ingestao_metadados(payload: dict):
    id_msg = payload.get("id_msg")
    dados = payload.get("data", {})
    lote_id = dados.get("id")
    metadados = dados.get("metadados", [])

    if not id_msg:
        logger.error("Mensagem sem id_msg recebida. Ignorando.")
        return

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO lotes_metadados (id, event_id, nome_lote, base_legal, analista_responsavel)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (event_id) DO NOTHING
            RETURNING id;
            """,
            (lote_id, id_msg, dados["nome_lote"], dados["base_legal"], dados.get("analista_responsavel")),
        )
        
        lote_inserido = cur.fetchone()
        

        if not lote_inserido:
            logger.info(f"[Idempotência] Mensagem {id_msg} já processada. Ignorando metadados.")
            return 

        for m in metadados:
            cur.execute(
                """
                INSERT INTO metadados
                    (id, id_lote, origem, temporalidade, crm_responsavel,
                     tipo_dado, categoria, base_legal, criptografado, atores_com_acesso)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb);
                """,
                (
                    str(uuid4()), lote_id, m["origem"], m["temporalidade"], m.get("crm_responsavel"),
                    m["tipo_dado"], m["categoria"], m["base_legal"], m["criptografado"],
                    json.dumps(m.get("atores_com_acesso", [])),
                ),
            )

        conn.commit()
    total = len(metadados)
    #gere log
    with SessionLocal as db:
        outbox_msg = await publisher.create_log_msg(m.get("crm_responsavel"),
                                        "Ingestao de metadados")
        db.add(outbox_msg)
        db.commit()
    if total > 0:
        calcular_e_salvar(lote_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task_matriz = asyncio.create_task(
        consumer.iniciar_consumo_matriz(_processar_tarefa_matriz)
    )
    
    task_metadados = asyncio.create_task(
        consumer.iniciar_consumo_metadados(_processar_ingestao_metadados)
    )

    yield
    
    task_matriz.cancel()
    task_metadados.cancel()
    
    try:
        await task_matriz
        await task_metadados
    except asyncio.CancelledError:
        pass
        
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
