
export const PERFIS = Object.freeze({
  ANALISTA: "ANALISTA",
  DESENVOLVEDOR: "DESENVOLVEDOR",
});

const CHAVE = "segurasaude.sessao";

export function sessao() {
  try {
    const bruto = sessionStorage.getItem(CHAVE);
    return bruto ? JSON.parse(bruto) : null;
  } catch (e) {
    return null;
  }
}

export function entrar(nome, perfil) {
  if (!Object.values(PERFIS).includes(perfil)) throw new Error("Perfil invalido.");
  const dados = { nome: nome.trim(), perfil };
  try {
    sessionStorage.setItem(CHAVE, JSON.stringify(dados));
  } catch (e) {
  }
  return dados;
}

export function sair() {
  try {
    sessionStorage.removeItem(CHAVE);
  } catch (e) {
  }
  window.location.href = "index.html";
}

export function exigirPerfil(permitidos) {
  const s = sessao();
  if (!s) {
    window.location.href = "index.html";
    return null;
  }
  if (!permitidos.includes(s.perfil)) {
    window.location.href = "dashboard.html?negado=1";
    return null;
  }
  return s;
}
