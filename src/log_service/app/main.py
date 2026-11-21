import json
from fastapi import FastAPI, HTTPException, Query
from psycopg.errors import UniqueViolation
from app.db import get_connection
from app.schemas import AuditLogIn, SystemLogIn, LogCreatedOut

app = FastAPI(title="SeguraSaúde - Serviço de Log Append-Only")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/logs/audit", response_model=LogCreatedOut, status_code=201)
def create_audit_log(payload: AuditLogIn):
    query = """
        INSERT INTO audit_logs (event_id, actor_id, actor_role, action, resource, status, details)
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
        RETURNING id, event_id, timestamp;
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                query,
                (
                    str(payload.event_id),
                    payload.actor_id,
                    payload.actor_role,
                    payload.action,
                    payload.resource,
                    payload.status,
                    json.dumps(payload.details),
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return row
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="Evento já registrado (idempotência).")


@app.get("/logs/audit")
def list_audit_logs(limit: int = Query(50, ge=1, le=500)):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT %s;",
            (limit,),
        )
        return cur.fetchall()


@app.post("/logs/system", response_model=LogCreatedOut, status_code=201)
def create_system_log(payload: SystemLogIn):
    query = """
        INSERT INTO system_logs (event_id, service_name, level, message, context)
        VALUES (%s, %s, %s, %s, %s::jsonb)
        RETURNING id, event_id, timestamp;
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                query,
                (
                    str(payload.event_id),
                    payload.service_name,
                    payload.level,
                    payload.message,
                    json.dumps(payload.context),
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return row
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="Evento já registrado (idempotência).")


@app.get("/logs/system")
def list_system_logs(limit: int = Query(50, ge=1, le=500)):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM system_logs ORDER BY timestamp DESC LIMIT %s;",
            (limit,),
        )
        return cur.fetchall()
