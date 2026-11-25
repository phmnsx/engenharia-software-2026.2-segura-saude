from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import socket
from api.auth_routes import router as auth_router

from api.controlador_log import router as log_router
from api.controlador_metadados import router as metadados_router
from api.controlador_matriz import router as matriz_router
from common.rabbitmqconfig.connection import RabbitMQConnection

conn = RabbitMQConnection()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await conn.connect()
    app.state.rabbit_conn = conn
    yield

    await conn.close()

app = FastAPI(title="SeguraSaúde - API Gateway", lifespan=lifespan)

app.include_router(metadados_router)
app.include_router(matriz_router)
app.include_router(auth_router)
app.include_router(log_router)



@app.get("/")
async def read_root():
    return {"container_id": socket.gethostname()}


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/status")
async def status(request: Request):
    conn = request.app.state.rabbit_conn
    channel = await conn.get_channel()
    return {"status:": "ok", "connection": not channel.is_closed}