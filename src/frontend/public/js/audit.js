import { PERFIS, exigirPerfil } from "./auth.js";
import { listarAuditLogs, listarLogsSistema, registrarAuditLog, ApiError } from "./api.js";
import { el, limpar, mostrarAlerta, formatarData, montarSidebar } from "./ui.js";

const s = exigirPerfil([PERFIS.ANALISTA, PERFIS.DESENVOLVEDOR]);
if (s) iniciar(s);

function iniciar(sessao) {
  montarSidebar("audit", sessao);
  const alerta = document.getElementById("alerta");
  // RN06: apenas o desenvolvedor registra log de auditoria.
  if (sessao.perfil === PERFIS.DESENVOLVEDOR) prepararRegistro(sessao, alerta);
  carregarLogs(alerta);
}

function tabela(cabecalho, linhas) {
  const corpo = el("tbody");
  for (const celulas of linhas) corpo.append(el("tr", {}, ...celulas.map((c) => el("td", {}, c))));
  return el("table", {}, el("thead", {}, el("tr", {}, ...cabecalho.map((h) => el("th", { scope: "col" }, h)))), corpo);
}

function preencher(alvo, registros, vazio, cabecalho, linha) {
  limpar(alvo);
  if (!registros.length) {
    alvo.append(el("div", { class: "vazio" }, vazio));
    return;
  }
  alvo.append(tabela(cabecalho, registros.map(linha)));
}

async function carregarLogs(alerta) {
  try {
    const [audit, sistema] = await Promise.all([listarAuditLogs(100), listarLogsSistema(100)]);
    preencher(document.getElementById("logs"), audit, "Nenhum registro de auditoria.",
      ["Data/hora", "Ator", "Perfil", "Ação", "Recurso", "Motivo", "Status"],
      (l) => [formatarData(l.timestamp), l.actor_id, l.actor_role, l.action, l.resource, (l.details && l.details.motivo) || "—", l.status]);
    preencher(document.getElementById("logs-sistema"), sistema, "Nenhum log do sistema.",
      ["Data/hora", "Serviço", "Nível", "Mensagem"],
      (l) => [formatarData(l.timestamp), l.service_name, l.level, l.message]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      mostrarAlerta(alerta, "aviso", "A consulta de logs ainda não está exposta pelo gateway. Esta tela será ativada quando o endpoint existir.");
    } else {
      mostrarAlerta(alerta, "erro", e.message);
    }
  }
}

function prepararRegistro(sessao, alerta) {
  document.getElementById("registro").classList.remove("oculto");
  const form = document.getElementById("form-audit");
  const responsavel = document.getElementById("responsavel");
  const botao = document.getElementById("registrar");
  responsavel.value = sessao.nome;

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const acao = document.getElementById("acao").value;
    const recurso = document.getElementById("recurso").value.trim();
    const motivo = document.getElementById("motivo").value.trim();
    if (!acao || !recurso) {
      mostrarAlerta(alerta, "erro", "Informe a ação e o recurso auditado.");
      return;
    }
    if (!motivo) {
      mostrarAlerta(alerta, "erro", "O motivo da auditoria é obrigatório (RF005).");
      return;
    }
    botao.disabled = true;
    try {
      await registrarAuditLog({ actor_id: sessao.nome, actor_role: sessao.perfil, action: acao, resource: recurso, motivo });
      form.reset();
      responsavel.value = sessao.nome;
      mostrarAlerta(alerta, "ok", "Log de auditoria registrado. Ele não pode ser alterado nem excluído.");
      await carregarLogs(alerta);
    } catch (e) {
      mostrarAlerta(alerta, "erro", e.message);
    } finally {
      botao.disabled = false;
    }
  });
}
