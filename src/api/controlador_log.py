"""
ControladorLog – consulta de logs e registro manual de AuditLog (RF005).

Expõe no gateway a leitura dos logs do sistema e dos audit logs e o
registro de um AuditLog com motivo obrigatório. O gateway só encaminha
ao Serviço de Log; não há rota de alteração nem de exclusão, porque os
logs são append-only (RNF001, ASR01).
"""

import json
import os
import urllib.error
import urllib.request
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from api.schemas import AuditLogManualIn

LOG_SERVICE_URL = os.getenv("LOG_SERVICE_URL", "http://log-service:8000")
TIMEOUT_SEGUNDOS = 3.0

router = APIRouter(prefix="/logs", tags=["Logs"])


def _chamar_servico_log(metodo: str, caminho: str, corpo: dict | None = None):
    dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    req = urllib.request.Request(
        f"{LOG_SERVICE_URL}{caminho}",
        data=dados,
        headers={"Content-Type": "application/json"},
        method=metodo,
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEGUNDOS) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 409:
            raise HTTPException(status_code=409, detail="Evento já registrado.")
        raise HTTPException(
            status_code=502,
            detail="O Serviço de Log recusou a requisição.",
        )
    except (urllib.error.URLError, TimeoutError):
        # Registro manual não vai para o buffer local: o desenvolvedor
        # precisa saber que o AuditLog não foi gravado para tentar de novo.
        raise HTTPException(
            status_code=503,
            detail="Serviço de Log indisponível. O registro não foi gravado; tente novamente.",
        )


# ── GET /logs/audit (somente leitura) ──────────────────────────────────
@router.get("/audit")
def listar_audit_logs(limit: int = Query(50, ge=1, le=500)):
    """Lista os audit logs mais recentes."""
    return _chamar_servico_log("GET", f"/logs/audit?limit={limit}")


# ── GET /logs/system (somente leitura) ─────────────────────────────────
@router.get("/system")
def listar_logs_sistema(limit: int = Query(50, ge=1, le=500)):
    """Lista os logs do sistema mais recentes."""
    return _chamar_servico_log("GET", f"/logs/system?limit={limit}")


# ── POST /logs/audit (registro manual com motivo) ───────────────────────
@router.post("/audit", status_code=201)
def registrar_audit_log(payload: AuditLogManualIn):
    """Registra um AuditLog manual. O motivo é obrigatório (RF005)."""
    corpo = {
        "event_id": str(uuid4()),
        "actor_id": payload.actor_id,
        "actor_role": payload.actor_role,
        "action": payload.action,
        "resource": payload.resource,
        "status": "SUCCESS",
        "details": {"motivo": payload.motivo, "origem": "registro_manual"},
    }
    return _chamar_servico_log("POST", "/logs/audit", corpo)
