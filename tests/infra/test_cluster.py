from pathlib import Path
import subprocess
import time
import requests
import pytest
import json

COMPOSE_FILE = Path(__file__).parent.resolve() / "compose.test.yml"
URL_TEST = "http://localhost:8080"

def setup_module(module):
    print("[SETUP] Inicializando 3 instancias para o cluster")
    subprocess.run(
        f"docker compose -f {COMPOSE_FILE} down -v --remove-orphans",
        shell=True, check=False
    )
    try:
        subprocess.run(
            f"docker compose -f {COMPOSE_FILE} up -d --build",
            shell=True, check=True,
            capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        print("============== ERRO NO DOCKER COMPOSE ==============")
        print(e.stderr)
        print("============== LOGS DO GATEWAY-1 ==============")
        logs = subprocess.run(f"docker compose -f {COMPOSE_FILE} logs gateway-1", shell=True, capture_output=True, text=True)
        print(logs.stdout)
        raise


def teardown_module(module):
    print("[TEARDOWN] Derrubando cluster")
    subprocess.run(
        f"docker compose -f {COMPOSE_FILE} down -v --remove-orphans",
        shell=True, check=True
    )

def test_load_balancing():
    containers_atendidos = set()
    print("[TEST] Enviando requisicoes")
    for _ in range(20):
        response = requests.get(URL_TEST)
        container_id = response.json().get("container_id")
        containers_atendidos.add(container_id)

    assert len(containers_atendidos) >= 2, "O Nginx não atendeu a todos os containers"
    print(f"[DONE] Requisições chegaram a {containers_atendidos} containers")

def test_resilience():
    print("[TEST] Matando um container e vendo se o sistema ainda funciona")
    subprocess.run(f"docker compose -f {COMPOSE_FILE} kill gateway-1", shell=True, check=True)

    time.sleep(5) #Tempo para o nginx
    for _ in range(10):
        response = requests.get(URL_TEST)
        assert response.status_code == 200, "O sistema caiu apos a queda de um container"
    print("[OK] O sistema continua bem")
