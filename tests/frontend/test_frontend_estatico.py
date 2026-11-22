import re
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PUBLIC = RAIZ / "src" / "frontend" / "public"
PAGINAS = ["index", "dashboard", "lote", "formulario", "upload", "audit-log"]


class Coletor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def carregar(nome):
    c = Coletor()
    c.feed((PUBLIC / f"{nome}.html").read_text(encoding="utf-8"))
    return c.tags


def test_paginas_existem_e_referenciam_arquivos_reais():
    for nome in PAGINAS:
        tags = carregar(nome)
        assert any(t == "html" and a.get("lang") == "pt-BR" for t, a in tags), nome
        for tag, attrs in tags:
            alvo = attrs.get("src") if tag == "script" else attrs.get("href") if tag == "link" else None
            if alvo:
                assert (PUBLIC / alvo).is_file(), f"{nome}.html referencia arquivo inexistente: {alvo}"


def test_login_tem_nome_e_perfil():
    ids = {a.get("id") for _, a in carregar("index")}
    assert {"nome", "perfil", "form-login"} <= ids


def test_formularios_exigem_base_legal_rn01():
    for nome in ("formulario", "upload"):
        base = [a for t, a in carregar(nome) if a.get("id") == "base_legal"]
        assert base and "required" in base[0], f"{nome}: base_legal deve ser obrigatoria (RN01)"
    for js in ("formulario.js", "upload.js"):
        assert "RN01" in (PUBLIC / "js" / js).read_text(encoding="utf-8")


def test_rbac_paginas_do_analista_bloqueiam_desenvolvedor():
    for js in ("formulario.js", "upload.js"):
        texto = (PUBLIC / "js" / js).read_text(encoding="utf-8")
        assert "exigirPerfil([PERFIS.ANALISTA])" in texto, js
    menu = (PUBLIC / "js" / "ui.js").read_text(encoding="utf-8")
    for chave in ("formulario", "upload"):
        linha = next(l for l in menu.splitlines() if f'chave: "{chave}"' in l)
        assert "DESENVOLVEDOR" not in linha, f"menu {chave} nao pode aparecer ao desenvolvedor"


def test_audit_log_somente_leitura():
    js = (PUBLIC / "js" / "audit.js").read_text(encoding="utf-8")
    api = (PUBLIC / "js" / "api.js").read_text(encoding="utf-8")
    assert "DELETE" not in js and "PUT" not in js and "PATCH" not in js
    assert "/logs/audit" in api
    assert not re.search(r'method:\s*"(DELETE|PUT|PATCH)"', api)


def test_sem_innerhtml_nem_scripts_externos():
    for arq in list((PUBLIC / "js").glob("*.js")):
        assert "innerHTML" not in arq.read_text(encoding="utf-8"), f"{arq.name} usa innerHTML"
    for nome in PAGINAS:
        for tag, attrs in carregar(nome):
            if tag == "script":
                assert not attrs.get("src", "").startswith(("http:", "https:", "//")), nome
            assert "onclick" not in attrs


def test_nginx_principal_roteia_app_sem_quebrar_raiz():
    conf = (RAIZ / "infra" / "nginx" / "nginx.conf").read_text(encoding="utf-8")
    assert "location /app/" in conf and "proxy_pass http://frontend:80/" in conf
    assert "location / {" in conf and "gateway_cluster" in conf


def test_compose_define_servico_frontend():
    compose = (RAIZ / "compose.yml").read_text(encoding="utf-8")
    assert "frontend:" in compose and "./src/frontend" in compose
    assert (RAIZ / "src" / "frontend" / "Dockerfile").is_file()


def test_csv_modelo_de_colunas_coerente_com_api():
    schemas = (RAIZ / "src" / "api" / "schemas.py").read_text(encoding="utf-8")
    csv_js = (PUBLIC / "js" / "csv.js").read_text(encoding="utf-8")
    for col in ("origem", "temporalidade", "crm_responsavel", "tipo_dado", "categoria", "base_legal", "criptografado", "atores_com_acesso"):
        assert col in schemas and col in csv_js, col


def test_registro_audit_log_exige_motivo_e_e_do_desenvolvedor():
    ids = {a.get("id"): a for _, a in carregar("audit-log") if a.get("id")}
    assert "required" in ids["motivo"], "motivo deve ser obrigatorio (RF005)"
    assert "readonly" in ids["responsavel"]
    js = (PUBLIC / "js" / "audit.js").read_text(encoding="utf-8")
    assert "exigirPerfil([PERFIS.DESENVOLVEDOR])" in js and "RF005" in js, "tela so do desenvolvedor (RN06)"
    menu = (PUBLIC / "js" / "ui.js").read_text(encoding="utf-8")
    linha = next(l for l in menu.splitlines() if 'chave: "audit"' in l)
    assert "ANALISTA" not in linha, "menu Audit Log nao pode aparecer ao analista"
    api = (PUBLIC / "js" / "api.js").read_text(encoding="utf-8")
    assert re.search(r'request\("/logs/audit",\s*\{\s*method:\s*"POST"', api)
    assert "/logs/system" in api
