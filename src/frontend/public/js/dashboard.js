import { PERFIS, exigirPerfil } from "./auth.js";
import { listarLotes, obterMatriz } from "./api.js";
import { el, limpar, mostrarAlerta, formatarData, montarSidebar, NIVEIS } from "./ui.js";

const s = exigirPerfil([PERFIS.ANALISTA, PERFIS.DESENVOLVEDOR]);
if (s) iniciar(s);

async function iniciar(sessao) {
  montarSidebar("dashboard", sessao);
  const alerta = document.getElementById("alerta");
  if (new URLSearchParams(window.location.search).get("negado")) {
    mostrarAlerta(alerta, "aviso", "Seu perfil não tem acesso a essa funcionalidade.");
  }
  try {
    const lotes = await listarLotes(50);
    preencherKpis(lotes);
    preencherTabela(lotes);
    await preencherMatriz(lotes.slice(0, 10));
  } catch (e) {
    mostrarAlerta(alerta, "erro", e.message);
    preencherTabela([]);
    preencherMatriz([]);
  }
}

function preencherKpis(lotes) {
  document.getElementById("kpi-lotes").textContent = String(lotes.length);
  document.getElementById("kpi-metadados").textContent = String(lotes.reduce((t, l) => t + (l.total_metadados || 0), 0));
  document.getElementById("kpi-ultimo").textContent = lotes.length ? formatarData(lotes[0].data_criacao) : "—";
}

function preencherTabela(lotes) {
  const alvo = document.getElementById("lotes");
  limpar(alvo);
  if (!lotes.length) {
    alvo.append(el("div", { class: "vazio" }, "Nenhum lote cadastrado ainda."));
    return;
  }
  const corpo = el("tbody");
  for (const l of lotes) {
    corpo.append(
      el("tr", {},
        el("td", {}, el("a", { href: `lote.html?id=${encodeURIComponent(l.id)}` }, l.nome_lote)),
        el("td", {}, l.base_legal),
        el("td", {}, l.analista_responsavel || "—"),
        el("td", {}, String(l.total_metadados)),
        el("td", {}, formatarData(l.data_criacao)),
      ),
    );
  }
  alvo.append(
    el("table", {},
      el("thead", {}, el("tr", {}, ...["Lote", "Base legal", "Analista", "Metadados", "Criado em"].map((h) => el("th", { scope: "col" }, h)))),
      corpo,
    ),
  );
}

async function preencherMatriz(lotes) {
  const alvo = document.getElementById("matriz");
  limpar(alvo);
  const resultados = await Promise.allSettled(lotes.map((l) => obterMatriz(l.id)));
  const matrizes = resultados.filter((r) => r.status === "fulfilled" && r.value).map((r) => r.value);
  if (!matrizes.length) {
    alvo.append(el("div", { class: "vazio" }, "Matriz ainda não calculada. O serviço de cálculo (RF001/RF002) será integrado nesta tela quando estiver disponível."));
    return;
  }
  const grade = el("div", { class: "matriz", role: "list" });
  for (const n of NIVEIS) {
    const qtd = matrizes.filter((m) => m.nivel_risco === n.valor).length;
    grade.append(el("div", { class: `celula ${n.chave}`, role: "listitem" }, el("div", { class: "n" }, String(qtd)), el("div", {}, n.rotulo)));
  }
  alvo.append(grade);
}
