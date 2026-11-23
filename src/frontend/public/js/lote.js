import { PERFIS, exigirPerfil } from "./auth.js";
import { obterLote, obterMatriz } from "./api.js";
import { el, limpar, mostrarAlerta, formatarData, montarSidebar, naoInformado, badgeNivel } from "./ui.js";

const s = exigirPerfil([PERFIS.ANALISTA, PERFIS.DESENVOLVEDOR]);
if (s) iniciar(s);

async function iniciar(sessao) {
  montarSidebar("dashboard", sessao);
  const alerta = document.getElementById("alerta");
  const id = new URLSearchParams(window.location.search).get("id");
  if (!id) {
    mostrarAlerta(alerta, "erro", "Lote não informado.");
    return;
  }
  try {
    const lote = await obterLote(id);
    document.getElementById("titulo").textContent = lote.nome_lote;
    renderResumo(lote);
    renderMetadados(lote.metadados);
    renderRisco(await obterMatriz(id));
  } catch (e) {
    mostrarAlerta(alerta, "erro", e.status === 404 ? "Lote não encontrado." : e.message);
  }
}

function renderResumo(lote) {
  const alvo = document.getElementById("resumo-corpo");
  limpar(alvo);
  alvo.append(
    el("p", {}, el("strong", {}, "Base legal: "), lote.base_legal),
    el("p", {}, el("strong", {}, "Analista: "), lote.analista_responsavel || "—"),
    el("p", {}, el("strong", {}, "Criado em: "), formatarData(lote.data_criacao)),
  );
}

function renderRisco(matriz) {
  const alvo = document.getElementById("risco");
  limpar(alvo);
  if (!matriz) {
    alvo.append(el("div", { class: "vazio" }, "Matriz ainda não calculada para este lote."));
    return;
  }
  alvo.append(el("p", {}, badgeNivel(matriz.nivel_risco)), el("p", {}, matriz.recomendacao_acao), el("p", { class: "dica" }, `Calculada em ${formatarData(matriz.data_hora)}`));
}

function renderMetadados(lista) {
  const alvo = document.getElementById("metadados");
  limpar(alvo);
  if (!lista.length) {
    alvo.append(el("div", { class: "vazio" }, "Este lote não possui metadados."));
    return;
  }
  const corpo = el("tbody");
  for (const m of lista) {
    corpo.append(
      el("tr", {},
        el("td", {}, m.origem),
        el("td", {}, m.temporalidade),
        el("td", {}, m.crm_responsavel),
        el("td", {}, naoInformado(m.tipo_dado)),
        el("td", {}, naoInformado(m.categoria)),
        el("td", {}, naoInformado(m.base_legal)),
        el("td", {}, m.criptografado ? "Sim" : el("span", { class: "nao-informado" }, "Não")),
        el("td", {}, m.atores_com_acesso.length ? m.atores_com_acesso.join(", ") : naoInformado(null)),
      ),
    );
  }
  const cab = ["Origem", "Temporalidade", "CRM", "Tipo", "Categoria", "Base legal", "Criptografado", "Atores com acesso"];
  alvo.append(el("table", {}, el("thead", {}, el("tr", {}, ...cab.map((h) => el("th", { scope: "col" }, h)))), corpo));
}
