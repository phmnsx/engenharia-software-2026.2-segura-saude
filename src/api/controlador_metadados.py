"""
ControladorMetadados – Endpoints de ingestão de lotes de metadados (RF004, RN01).

Aceita lotes via JSON ou formulário, valida obrigatoriamente a base legal
da LGPD (RN01) e dispara registro automático no Serviço de Log (LogSistema).
"""

import json
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Form, HTTPException, UploadFile, File, Query
from typing import Optional

from api.db import get_connection
from api.schemas import (
    LoteMetadadosIn,
    LoteMetadadosOut,
    LoteMetadadosSummaryOut,
    MetadadosOut,
)
from api.servico_matriz import calcular_e_salvar
from common.log_client import send_system_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadados", tags=["Metadados"])


# ── POST /metadados/lotes (JSON) ────────────────────────────────────────
@router.post("/lotes", response_model=LoteMetadadosSummaryOut, status_code=201)
def criar_lote_json(payload: LoteMetadadosIn):
    """Recebe um lote de metadados via payload JSON."""
    return _persistir_lote(payload)


# ── POST /metadados/lotes/form (Formulário) ─────────────────────────────
@router.post("/lotes/form", response_model=LoteMetadadosSummaryOut, status_code=201)
def criar_lote_formulario(
    nome_lote: str = Form(...),
    base_legal: str = Form(...),
    analista_responsavel: Optional[str] = Form(None),
    metadados_json: Optional[str] = Form(None),
):
    """Recebe um lote de metadados via campos de formulário."""
    if not base_legal or not base_legal.strip():
        raise HTTPException(
            status_code=400,
            detail="Campo 'base_legal' é obrigatório (RN01 – LGPD).",
        )

    metadados_list = []
    if metadados_json:
        try:
            metadados_list = json.loads(metadados_json)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Campo 'metadados_json' contém JSON inválido.",
            )

    payload = LoteMetadadosIn(
        nome_lote=nome_lote,
        base_legal=base_legal,
        analista_responsavel=analista_responsavel,
        metadados=metadados_list,
    )
    return _persistir_lote(payload)


# ── GET /metadados/lotes ────────────────────────────────────────────────
@router.get("/lotes", response_model=list[LoteMetadadosSummaryOut])
def listar_lotes(limit: int = Query(50, ge=1, le=500)):
    """Lista os lotes de metadados cadastrados."""
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


# ── GET /metadados/lotes/{lote_id} ──────────────────────────────────────
@router.get("/lotes/{lote_id}", response_model=LoteMetadadosOut)
def obter_lote(lote_id: UUID):
    """Retorna um lote com seus metadados."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM lotes_metadados WHERE id = %s;", (lote_id,))
        lote = cur.fetchone()
        if not lote:
            raise HTTPException(status_code=404, detail="Lote não encontrado.")

        cur.execute(
            "SELECT * FROM metadados WHERE id_lote = %s;", (lote_id,)
        )
        lote["metadados"] = cur.fetchall()
        return lote


# ── Lógica de persistência compartilhada ────────────────────────────────
def _persistir_lote(payload: LoteMetadadosIn) -> dict:
    lote_id = str(uuid4())

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO lotes_metadados (id, nome_lote, base_legal, analista_responsavel)
            VALUES (%s, %s, %s, %s)
            RETURNING id, nome_lote, base_legal, analista_responsavel, data_criacao;
            """,
            (lote_id, payload.nome_lote, payload.base_legal, payload.analista_responsavel),
        )
        lote_row = cur.fetchone()

        for m in payload.metadados:
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
                    m.origem,
                    m.temporalidade,
                    m.crm_responsavel,
                    m.tipo_dado,
                    m.categoria,
                    m.base_legal,
                    m.criptografado,
                    json.dumps(m.atores_com_acesso),
                ),
            )

        conn.commit()

    total = len(payload.metadados)
    lote_row["total_metadados"] = total

    # Disparo automático de log de sistema (LogSistema)
    send_system_log(
        service_name="api-gateway",
        level="INFO",
        message=f"Lote de metadados '{payload.nome_lote}' criado com {total} registro(s).",
        context={
            "lote_id": lote_id,
            "base_legal": payload.base_legal,
            "analista": payload.analista_responsavel,
            "total_metadados": total,
        },
    )

    # Cálculo automático da matriz na ingestão (se total > 0)
    if total > 0:
        try:
            calcular_e_salvar(lote_id)
        except Exception as exc:
            logger.error("Falha ao calcular matriz para o lote %s: %s", lote_id, exc, exc_info=True)
            send_system_log(
                service_name="api-gateway",
                level="ERROR",
                message=f"Falha ao calcular matriz automaticamente para o lote '{payload.nome_lote}': {exc}",
                context={
                    "lote_id": lote_id,
                    "erro": str(exc),
                },
            )

    return lote_row
