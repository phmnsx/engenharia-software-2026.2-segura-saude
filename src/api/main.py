from fastapi import FastAPI
import socket
from api.auth_routes import router as auth_router

from api.controlador_log import router as log_router
from api.controlador_metadados import router as metadados_router
from api.controlador_matriz import router as matriz_router

app = FastAPI(title="SeguraSaúde - API Gateway")

app.include_router(metadados_router)
app.include_router(matriz_router)
app.include_router(auth_router)
app.include_router(log_router)


@app.get("/")
def read_root():
    return {"container_id": socket.gethostname()}


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/health/connection")
def health_connection():
    return {"status:" "ok"}