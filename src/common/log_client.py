import json
import os
from pathlib import Path
from uuid import uuid4
import urllib.request
import urllib.error

LOG_SERVICE_URL = os.getenv("LOG_SERVICE_URL", "http://log-service:8000")
LOCAL_BUFFER_PATH = Path(os.getenv("LOG_LOCAL_BUFFER", "/tmp/segurasaude_log_buffer.jsonl"))


def send_audit_log(actor_id: str, actor_role: str, action: str, resource: str, status: str, details: dict | None = None) -> bool:
    payload = {
        "event_id": str(uuid4()),
        "actor_id": actor_id,
        "actor_role": actor_role,
        "action": action,
        "resource": resource,
        "status": status,
        "details": details or {},
    }
    return _post_or_buffer("/logs/audit", payload)


def _post_or_buffer(endpoint: str, payload: dict) -> bool:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{LOG_SERVICE_URL}{endpoint}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError):
        with LOCAL_BUFFER_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"endpoint": endpoint, "payload": payload}) + "\n")
        return False
