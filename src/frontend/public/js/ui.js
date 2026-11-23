import { PERFIS, sair } from "./auth.js";

export function el(tag, atributos = {}, ...filhos) {
  const no = document.createElement(tag);
  for (const [k, v] of Object.entries(atributos)) {
    if (k === "class") no.className = v;
    else if (v !== null && v !== undefined) no.setAttribute(k, v);
  }
  for (const f of filhos) {
    if (f === null || f === undefined) continue;
    no.append(f instanceof Node ? f : document.createTextNode(String(f)));
  }
  return no;
}

export function limpar(no) {
  while (no.firstChild) no.removeChild(no.firstChild);
}

export function mostrarAlerta(container, tipo, mensagem) {
  limpar(container);
  if (!mensagem) return;
  container.append(el("div", { class: `alerta ${tipo}`, role: tipo === "erro" ? "alert" : "status" }, mensagem));
}

export function formatarData(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString("pt-BR");
}

export function naoInformado(valor) {
  if (valor === null || valor === undefined || valor === "") {
    return el("span", { class: "nao-informado" }, "Não informado");
  }
  return String(valor);
}

export const NIVEIS = [
  { valor: 0, chave: "baixo", rotulo: "Baixo" },
  { valor: 1, chave: "medio", rotulo: "Médio" },
  { valor: 2, chave: "alto", rotulo: "Alto" },
  { valor: 3, chave: "critico", rotulo: "Crítico" },
];

export function badgeNivel(nivel) {
  const n = NIVEIS.find((x) => x.valor === nivel);
  return n ? el("span", { class: `badge ${n.chave}` }, n.rotulo) : el("span", { class: "badge neutro" }, "Não calculado");
}

const MENU = [
  { chave: "dashboard", href: "dashboard.html", rotulo: "Dashboard", perfis: [PERFIS.ANALISTA, PERFIS.DESENVOLVEDOR] },
  { chave: "formulario", href: "formulario.html", rotulo: "Formulário", perfis: [PERFIS.ANALISTA] },
  { chave: "upload", href: "upload.html", rotulo: "Upload JSON/CSV", perfis: [PERFIS.ANALISTA] },
  { chave: "audit", href: "audit-log.html", rotulo: "Audit Log", perfis: [PERFIS.DESENVOLVEDOR] },
];

export function montarSidebar(ativo, sessao) {
  const nav = el("nav", { "aria-label": "Principal" });
  for (const item of MENU.filter((m) => m.perfis.includes(sessao.perfil))) {
    nav.append(el("a", { href: item.href, class: item.chave === ativo ? "ativo" : "", "aria-current": item.chave === ativo ? "page" : null }, item.rotulo));
  }
  const botaoSair = el("button", { type: "button", class: "btn secundario" }, "Sair");
  botaoSair.addEventListener("click", sair);
  const aside = el(
    "aside",
    { class: "sidebar" },
    el("div", { class: "brand" }, "Segura", el("span", {}, "Saúde")),
    nav,
    el("div", { class: "usuario" }, el("div", {}, sessao.nome), el("div", {}, sessao.perfil === PERFIS.ANALISTA ? "Analista" : "Desenvolvedor"), botaoSair),
  );
  document.querySelector(".layout").prepend(aside);
}
