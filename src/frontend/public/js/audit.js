import { PERFIS, exigirPerfil } from "./auth.js";
import { listarAuditLogs, ApiError } from "./api.js";
import { el, limpar, mostrarAlerta, formatarData, montarSidebar } from "./ui.js";

const s = exigirPerfil([PERFIS.ANALISTA, PERFIS.DESENVOLVEDOR]);
if (s) iniciar(s);

async function iniciar(sessao) {
  montarSidebar("audit", sessao);
  const alerta = document.getElementById("alerta");
  const alvo = document.getElementById("logs");
  try {
    const logs = await listarAuditLogs(100);
    limpar(alvo);
    if (!logs.length) {
      alvo.append(el("div", { class: "vazio" }, "Nenhum registro de auditoria."));
      return;
    }
    const corpo = el("tbody");
    for (const l of logs) {
      corpo.append(el("tr", {}, el("td", {}, formatarData(l.timestamp)), el("td", {}, l.actor_id), el("td", {}, l.actor_role), el("td", {}, l.action), el("td", {}, l.resource), el("td", {}, l.status)));
    }
    const cab = ["Data/hora", "Ator", "Perfil", "Ação", "Recurso", "Status"];
    alvo.append(el("table", {}, el("thead", {}, el("tr", {}, ...cab.map((h) => el("th", { scope: "col" }, h)))), corpo));
  } catch (e) {
    if (e instanceof ApiError && (e.status === 404 || e.status === 503)) {
      mostrarAlerta(alerta, "aviso", "A consulta de logs ainda não está exposta pelo gateway. Esta tela será ativada quando o endpoint existir.");
    } else {
      mostrarAlerta(alerta, "erro", e.message);
    }
  }
}
