import { entrar, sessao } from "./auth.js";
import { mostrarAlerta } from "./ui.js";

if (sessao()) window.location.href = "dashboard.html";

document.getElementById("form-login").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const nome = document.getElementById("nome").value;
  const perfil = document.getElementById("perfil").value;
  const alerta = document.getElementById("alerta");
  if (!nome.trim()) {
    mostrarAlerta(alerta, "erro", "Informe o nome.");
    return;
  }
  entrar(nome, perfil);
  window.location.href = "dashboard.html";
});
