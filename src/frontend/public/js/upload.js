import { PERFIS, exigirPerfil } from "./auth.js";
import { criarLote } from "./api.js";
import { metadadosDeCsv, metadadosDeJson } from "./csv.js";
import { el, limpar, mostrarAlerta, montarSidebar } from "./ui.js";

const MAX_BYTES = 10 * 1024 * 1024;
const s = exigirPerfil([PERFIS.ANALISTA]);
if (s) iniciar(s);

function iniciar(sessao) {
  montarSidebar("upload", sessao);
  const alerta = document.getElementById("alerta");
  const previa = document.getElementById("previa");
  const botao = document.getElementById("enviar");
  let metadados = null;

  document.getElementById("arquivo").addEventListener("change", async (ev) => {
    metadados = null;
    botao.disabled = true;
    limpar(previa);
    mostrarAlerta(alerta, "", "");
    const arquivo = ev.target.files[0];
    if (!arquivo) return;
    if (arquivo.size > MAX_BYTES) return mostrarAlerta(alerta, "erro", "Arquivo maior que 10 MB.");
    const nome = arquivo.name.toLowerCase();
    try {
      const texto = await arquivo.text();
      if (nome.endsWith(".json")) metadados = metadadosDeJson(texto);
      else if (nome.endsWith(".csv")) metadados = metadadosDeCsv(texto);
      else throw new Error("Formato não suportado. Use .json ou .csv.");
      previa.append(el("div", { class: "alerta info" }, `${metadados.length} metadado(s) lido(s) de ${arquivo.name}.`));
      botao.disabled = false;
    } catch (e) {
      mostrarAlerta(alerta, "erro", e.message);
    }
  });

  document.getElementById("form-upload").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const nome = document.getElementById("nome_lote").value.trim();
    const baseLegal = document.getElementById("base_legal").value.trim();
    if (!nome) return mostrarAlerta(alerta, "erro", "Informe o nome do lote.");
    if (!baseLegal) return mostrarAlerta(alerta, "erro", "A base legal é obrigatória (RN01).");
    if (!metadados) return mostrarAlerta(alerta, "erro", "Selecione um arquivo válido.");
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
