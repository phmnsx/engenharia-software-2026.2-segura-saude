import asyncio
import json
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query

from app.db import get_connection
from app.schemas import AuditLogIn, SystemLogIn
from common.rabbitmqconfig.consumer import RabbitMQConsumer

logger = logging.getLogger(__name__)
consumer = RabbitMQConsumer()


def _inserir_audit_log(dados: dict) -> dict:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO audit_logs
                (event_id, actor_id, actor_role, action, resource, status, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (event_id) DO NOTHING
            RETURNING *;
            """,
            (
                dados.get("event_id") or str(uuid4()),
                dados.get("actor_id") or dados.get("usuario", "sistema"),
                dados.get("actor_role", "DESCONHECIDO"),
                dados.get("action") or dados.get("acao", "EVENTO"),
                dados.get("resource", "sistema"),
                dados.get("status", "SUCCESS"),
                json.dumps(dados.get("details") or {}),
            ),
        )
        row = cur.fetchone()
        conn.commit()
    return row or dados


async def _processar_log_da_fila(payload: dict):
    """Recebe o envelope do RabbitMQPublisher e grava o AuditLog no banco."""
    event_id = payload.get("id_msg")
    data = payload.get("data", {})
    
    if not event_id:
        logger.error("Mensagem sem id_msg recebida. Ignorando.")
        return

    row = _inserir_audit_log(
        {
            "event_id": event_id,
            "actor_id": data.get("usuario", "sistema"),
            "actor_role": "SISTEMA", 
            "action": data.get("acao", "LOG"),
            "resource": "rabbitmq",
            "status": "SUCCESS",
            "details": data.get("detalhes", {}),
        }
    )
    
    if row is None:
        logger.info(f"[Idempotência] Evento {event_id} já registrado. Ignorando duplicata.")
    else:
        logger.info(f"[Log] Evento {event_id} registrado com sucesso.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    task_consumer = asyncio.create_task(
        consumer.iniciar_consumo_logs(_processar_log_da_fila)
    )
    yield
    task_consumer.cancel()
    try:
        await task_consumer
    except asyncio.CancelledError:
        pass 
    await consumer.conn_manager.close()


app = FastAPI(title="SeguraSaúde - Log Service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/logs/audit")
def listar_audit_logs(limit: int = Query(50, ge=1, le=500)):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT %s;",
            (limit,),
        )
        return cur.fetchall()


@app.get("/logs/system")
def listar_logs_sistema(limit: int = Query(50, ge=1, le=500)):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM system_logs ORDER BY created_at DESC LIMIT %s;",
            (limit,),
        )
        return cur.fetchall()

"""
@app.post("/logs/audit", status_code=201)
def criar_audit_log(payload: AuditLogIn):
    row = _inserir_audit_log(payload.model_dump())
    if not row:
        raise HTTPException(status_code=409, detail="Evento já registrado.")
    return row


@app.post("/logs/system", status_code=201)
def criar_system_log(payload: SystemLogIn):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            
            INSERT INTO system_logs (event_id, service_name, level, message, context)
            VALUES (%s, %s, %s, %s::jsonb)
            ON CONFLICT (event_id) DO NOTHING
            RETURNING *;
            ,
            (
                payload.event_id,
                payload.service_name,
                payload.level,
                payload.message,
                json.dumps(payload.context or {}),
            ),
        )
        row = cur.fetchone()
        conn.commit()
        if not row:
            raise HTTPException(status_code=409, detail="Evento de sistema já registrado.")
    return row
"""