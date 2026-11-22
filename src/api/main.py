from fastapi import FastAPI
import socket
from auth_routes import router as auth_router

from api.controlador_metadados import router as metadados_router

app = FastAPI(title="SeguraSaúde - API Gateway")

app.include_router(metadados_router)

app = FastAPI()
app.include_router(auth_router)

@app.get("/")
def read_root():
    return {"container_id": socket.gethostname()}


@app.get("/health")
def health():
    return {"status": "ok"}
