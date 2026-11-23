
export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function formatarDetalhe(detail) {
  if (!detail) return "Erro inesperado.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("; ");
  }
  return JSON.stringify(detail);
}

async function request(path, options = {}) {
  let resp;
  try {
    resp = await fetch(path, options);
  } catch (e) {
    throw new ApiError(0, "Sem conexao com o servidor. Tente novamente.");
  }
  let corpo = null;
  try {
    corpo = await resp.json();
  } catch (e) {
    corpo = null;
  }
  if (!resp.ok) {
    throw new ApiError(resp.status, formatarDetalhe(corpo && corpo.detail));
  }
  return corpo;
}

const JSON_HEADERS = { "Content-Type": "application/json" };

export const listarLotes = (limit = 50) => request(`/metadados/lotes?limit=${limit}`);
export const obterLote = (id) => request(`/metadados/lotes/${encodeURIComponent(id)}`);
export const criarLote = (payload) =>
  request("/metadados/lotes", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });

export async function obterMatriz(idLote) {
  try {
    return await request(`/matriz/lotes/${encodeURIComponent(idLote)}`);
  } catch (e) {
    if (e instanceof ApiError && (e.status === 404 || e.status === 503)) return null;
    throw e;
  }
}

export const listarAuditLogs = (limit = 100) => request(`/logs/audit?limit=${limit}`);
export const listarLogsSistema = (limit = 100) => request(`/logs/system?limit=${limit}`);
export const registrarAuditLog = (payload) =>
  request("/logs/audit", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });
