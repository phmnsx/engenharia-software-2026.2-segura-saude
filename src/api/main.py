from fastapi import FastAPI
import socket

app = FastAPI()

@app.get("/")
def read_root():
    return {"container_id": socket.gethostname()}