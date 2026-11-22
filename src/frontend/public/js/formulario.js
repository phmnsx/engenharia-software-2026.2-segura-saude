import { PERFIS, exigirPerfil } from "./auth.js";
import { criarLote } from "./api.js";
import { el, mostrarAlerta, montarSidebar } from "./ui.js";

const s = exigirPerfil([PERFIS.ANALISTA]);
if (s) iniciar(s);

function iniciar(sessao) {
  montarSidebar("formulario", sessao);
  const itens = document.getElementById("itens");
  const alerta = document.getElementById("alerta");
  const form = document.getElementById("form-lote");
  const botao = document.getElementById("enviar");

  adicionarItem(itens);
  document.getElementById("add-item").addEventListener("click", () => adicionarItem(itens));

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const nome = document.getElementById("nome_lote").value.trim();
    const baseLegal = document.getElementById("base_legal").value.trim();
    if (!nome) return mostrarAlerta(alerta, "erro", "Informe o nome do lote.");
    if (!baseLegal) return mostrarAlerta(alerta, "erro", "A base legal é obrigatória (RN01).");

    let metadados;
    try {
      metadados = lerItens(itens);
    } catch (e) {
      return mostrarAlerta(alerta, "erro", e.message);
    }

    botao.disabled = true;
    try {
      const lote = await criarLote({ nome_lote: nome, base_legal: baseLegal, analista_responsavel: sessao.nome, metadados });
      window.location.href = `lote.html?id=${encodeURIComponent(lote.id)}`;
    } catch (e) {
      mostrarAlerta(alerta, "erro", e.message);
      botao.disabled = false;
    }
  });
}

function campo(rotulo, nome, obrigatorio = false) {
  const id = `${nome}-${Math.random().toString(36).slice(2, 8)}`;
  return el("div", {}, el("label", { for: id }, obrigatorio ? `${rotulo} *` : rotulo), el("input", { type: "text", id, "data-campo": nome, maxlength: "200" }));
}

function adicionarItem(container) {
  const n = container.children.length + 1;
  const chk = el("input", { type: "checkbox", "data-campo": "criptografado", id: `crip-${n}-${Math.random().toString(36).slice(2, 6)}` });
  const remover = el("button", { type: "button", class: "btn secundario" }, "Remover");
  const bloco = el(
    "fieldset",
    { class: "card" },
    el("legend", {}, `Metadado ${n}`),
    campo("Origem", "origem", true),
    campo("Temporalidade", "temporalidade", true),
    campo("CRM responsável", "crm_responsavel", true),
    campo("Tipo de dado", "tipo_dado"),
    campo("Categoria", "categoria"),
    campo("Base legal do dado", "base_legal"),
    campo("Atores com acesso (separados por vírgula)", "atores_com_acesso"),
    el("label", { for: chk.id }, chk, " Criptografado em repouso"),
    remover,
  );
  remover.addEventListener("click", () => bloco.remove());
  container.append(bloco);
}

function lerItens(container) {
  return Array.from(container.children).map((bloco, i) => {
    const v = (nome) => bloco.querySelector(`[data-campo="${nome}"]`);
    const txt = (nome) => v(nome).value.trim();
    for (const obrig of ["origem", "temporalidade", "crm_responsavel"]) {
      if (!txt(obrig)) throw new Error(`Metadado ${i + 1}: preencha ${obrig}.`);
    }
    return {
      origem: txt("origem"),
      temporalidade: txt("temporalidade"),
      crm_responsavel: txt("crm_responsavel"),
      tipo_dado: txt("tipo_dado") || null,
      categoria: txt("categoria") || null,
      base_legal: txt("base_legal") || null,
      criptografado: v("criptografado").checked,
      atores_com_acesso: txt("atores_com_acesso").split(",").map((a) => a.trim()).filter(Boolean),
    };
  });
}
