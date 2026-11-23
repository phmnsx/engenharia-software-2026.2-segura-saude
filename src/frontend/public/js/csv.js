
export function parseCsv(texto) {
  const linhas = [];
  let campo = "";
  let linha = [];
  let aspas = false;
  const s = texto.replace(/^﻿/, "");
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (aspas) {
      if (c === '"' && s[i + 1] === '"') { campo += '"'; i++; }
      else if (c === '"') aspas = false;
      else campo += c;
    } else if (c === '"') aspas = true;
    else if (c === ",") { linha.push(campo); campo = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && s[i + 1] === "\n") i++;
      linha.push(campo); campo = "";
      if (linha.some((x) => x.trim() !== "")) linhas.push(linha);
      linha = [];
    } else campo += c;
  }
  linha.push(campo);
  if (linha.some((x) => x.trim() !== "")) linhas.push(linha);
  return linhas;
}

const OBRIGATORIAS = ["origem", "temporalidade", "crm_responsavel"];

function textoOuNull(v) {
  const t = (v || "").trim();
  return t === "" ? null : t;
}

function paraBool(v) {
  return ["true", "1", "sim", "s", "yes"].includes((v || "").trim().toLowerCase());
}

export function metadadosDeCsv(texto) {
  const linhas = parseCsv(texto);
  if (linhas.length < 2) throw new Error("O CSV precisa de cabeçalho e ao menos uma linha.");
  const cab = linhas[0].map((h) => h.trim().toLowerCase());
  for (const col of OBRIGATORIAS) {
    if (!cab.includes(col)) throw new Error(`Coluna obrigatória ausente no CSV: ${col}`);
  }
  const idx = (nome) => cab.indexOf(nome);
  return linhas.slice(1).map((l, n) => {
    const pega = (nome) => (idx(nome) >= 0 ? l[idx(nome)] : "");
    const item = {
      origem: (pega("origem") || "").trim(),
      temporalidade: (pega("temporalidade") || "").trim(),
      crm_responsavel: (pega("crm_responsavel") || "").trim(),
      tipo_dado: textoOuNull(pega("tipo_dado")),
      categoria: textoOuNull(pega("categoria")),
      base_legal: textoOuNull(pega("base_legal")),
      criptografado: paraBool(pega("criptografado")),
      atores_com_acesso: (pega("atores_com_acesso") || "").split(";").map((a) => a.trim()).filter(Boolean),
    };
    for (const col of OBRIGATORIAS) {
      if (!item[col]) throw new Error(`Linha ${n + 2}: campo obrigatório vazio (${col}).`);
    }
    return item;
  });
}

export function metadadosDeJson(texto) {
  let dados;
  try {
    dados = JSON.parse(texto);
  } catch (e) {
    throw new Error("JSON inválido.");
  }
  const lista = Array.isArray(dados) ? dados : dados && dados.metadados;
  if (!Array.isArray(lista)) throw new Error('O JSON deve ser uma lista ou um objeto com a chave "metadados".');
  lista.forEach((m, n) => {
    for (const col of OBRIGATORIAS) {
      if (!m || typeof m[col] !== "string" || !m[col].trim()) {
        throw new Error(`Item ${n + 1}: campo obrigatório ausente (${col}).`);
      }
    }
  });
  return lista;
}
