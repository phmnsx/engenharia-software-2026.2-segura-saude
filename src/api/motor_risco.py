"""
Motor de Cálculo Síncrono da Matriz de Risco (RF001, DT03).

Implementa a regra direta de cálculo baseada na LGPD (Lei Geral de Proteção de
Dados Pessoais - Lei nº 13.709/2018), sem frameworks complexos (DT03) e com
execução síncrona em memória (DT02).

Cruza três dimensões essenciais para cada metadado do lote:
  1. Sensibilidade do dado (Art. 5º, I e II, e Art. 11 da LGPD):
     - Dados sensíveis de saúde (CID, diagnóstico, prontuário, biometria): Peso 3
     - Dados pessoais comuns/PII (CPF, RG, nome, contato): Peso 2
     - Dados gerais/técnicos (setor, timestamp, código de leito): Peso 1
  2. Ausência de criptografia (Art. 46 da LGPD):
     - Dados não criptografados aumentam o risco de exposição.
  3. Atores com acesso (Art. 6º, III - Princípio da Necessidade/Need-to-know):
     - Superfície de acesso ampla (> 3 atores) ou presença de atores
       não-clínicos/terceiros com acesso a dados sensíveis eleva o risco.

Consolida o nível de risco do lote (pior caso / elo mais fraco) e gera a
ação recomendada correspondente (Criptografar, Remover acesso, Manter log).
"""

from functools import lru_cache
import re
from typing import Any, Dict, List, Tuple
import unicodedata
from api.models import NivelRisco

# Termos associados a dados sensíveis de saúde (LGPD Art. 5º, II e Art. 11)
# Nota: "tratamento" foi removido por ser ambíguo (ex.: tratamento de dados, tratamento de resíduos).
TERMOS_SENSIVEIS_SAUDE = frozenset({
    "cid",
    "diagnostico",
    "diagnóstico",
    "prontuario",
    "prontuário",
    "exame",
    "laudo",
    "receita",
    "prescricao",
    "prescrição",
    "patologia",
    "anamnese",
    "biometria",
    "genetico",
    "genético",
    "saude",
    "saúde",
    "doenca",
    "doença",
    "cirurgia",
})

# Termos associados a dados pessoais comuns identificáveis (PII - LGPD Art. 5º, I)
TERMOS_PII = frozenset({
    "cpf",
    "rg",
    "nome",
    "paciente",
    "telefone",
    "celular",
    "email",
    "e-mail",
    "endereco",
    "endereço",
    "nascimento",
    "identidade",
    "cns",
    "cartao_sus",
    "cartão_sus",
})

# Perfis de atores considerados não clínicos ou com necessidade de restrição estrita
ATORES_NAO_CLINICOS = frozenset({
    "terceiro",
    "terceiros",
    "marketing",
    "comercial",
    "estagiario",
    "estagiário",
    "externo",
    "visitante",
    "financeiro",
    "publico",
    "público",
})


def _sem_acento(s: str) -> str:
    """Remove acentos e caracteres diacríticos da string."""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


@lru_cache(maxsize=None)
def _regex(termos: frozenset) -> re.Pattern:
    """Compila expressão regular que casa palavras inteiras (usando bordas \\b)."""
    alternativas = "|".join(re.escape(_sem_acento(t)) for t in sorted(termos, key=len, reverse=True))
    return re.compile(rf"\b(?:{alternativas})\b")


def _contem(texto: str, termos: frozenset) -> bool:
    """Verifica se o texto contém algum dos termos como palavra inteira (case/acento-insensível)."""
    return bool(_regex(termos).search(_sem_acento(texto.lower())))


def _extrair_texto_normalizado(*valores: Any) -> str:
    """Combina e converte valores para texto minúsculo para busca de palavras-chave."""
    partes = []
    for v in valores:
        if v is not None:
            partes.append(str(v).strip().lower())
    return " ".join(partes)


def classificar_sensibilidade(origem: str = "", tipo_dado: str = "", categoria: str = "") -> Tuple[int, str]:
    """
    Classifica a sensibilidade do metadado conforme critérios da LGPD.

    Retorna:
        Tuple[int, str]: (peso_sensibilidade [1..3], rotulo_sensibilidade)
    """
    texto = _extrair_texto_normalizado(origem, tipo_dado, categoria)

    # 1. Verifica termos sensíveis de saúde (Art. 11 LGPD)
    if _contem(texto, TERMOS_SENSIVEIS_SAUDE):
        return 3, "SENSÍVEL_SAÚDE"

    # Se a categoria declarada contiver explicitamente 'sensivel'
    if _contem(texto, frozenset({"sensivel", "sensível"})):
        return 3, "SENSÍVEL_SAÚDE"

    # 2. Verifica dados pessoais comuns / identificadores (Art. 5º, I LGPD)
    if _contem(texto, TERMOS_PII):
        return 2, "PII_IDENTIFICADOR"

    # 3. Dado técnico ou geral
    return 1, "GERAL_TECNICO"


def avaliar_exposicao_atores(atores: List[str], peso_sensibilidade: int) -> Tuple[bool, List[str]]:
    """
    Avalia a superfície de exposição baseada na lista de atores com acesso.

    Retorna:
        Tuple[bool, List[str]]: (esta_exposto, lista_de_justificativas)
    """
    fatores: List[str] = []
    if not atores:
        return False, fatores

    # Excesso de atores (> 3 perfis/atores distintos com acesso)
    if len(atores) > 3:
        fatores.append(f"Acesso amplo concedido a {len(atores)} atores distintos (violando princípio do privilégio mínimo)")

    # Presença de atores não-clínicos com acesso a dados PII ou sensíveis
    if peso_sensibilidade >= 2:
        nao_clinicos_presentes = [
            str(a).strip() for a in atores if _contem(str(a), ATORES_NAO_CLINICOS)
        ]
        if nao_clinicos_presentes:
            fatores.append(
                f"Atores não-clínicos/externos com acesso a dados pessoais ou sensíveis: {', '.join(nao_clinicos_presentes)}"
            )

    esta_exposto = len(fatores) > 0
    return esta_exposto, fatores


def calcular_risco_metadado(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula o nível de risco de um metadado individual cruzando sensibilidade,
    criptografia e atores com acesso.

    Retorna dicionário com o nível de risco (0 a 3) e o detalhamento técnico.
    """
    origem = str(item.get("origem", ""))
    tipo_dado = str(item.get("tipo_dado", "") or "")
    categoria = str(item.get("categoria", "") or "")
    criptografado = bool(item.get("criptografado", False))
    atores = list(item.get("atores_com_acesso") or [])

    peso_sens, rotulo_sens = classificar_sensibilidade(origem, tipo_dado, categoria)
    exposto, fatores_exposicao = avaliar_exposicao_atores(atores, peso_sens)

    fatores: List[str] = []

    # Cálculo da pontuação direta LGPD (DT03)
    if peso_sens == 3:  # Dado sensível de saúde (ex: CID, diagnóstico, prontuário)
        if not criptografado and exposto:
            nivel = NivelRisco.CRITICO.value  # 3
            fatores.append("Dado sensível de saúde em texto claro com alta exposição de atores.")
        elif not criptografado and not exposto:
            nivel = NivelRisco.ALTO.value  # 2
            fatores.append("Dado sensível de saúde sem criptografia em repouso.")
        elif criptografado and exposto:
            nivel = NivelRisco.ALTO.value  # 2
            fatores.append("Dado sensível de saúde criptografado, porém exposto a múltiplos atores.")
        else:
            nivel = NivelRisco.MEDIO.value  # 1
            fatores.append("Dado sensível de saúde protegido por criptografia e acesso controlado.")

    elif peso_sens == 2:  # Dado pessoal comum / PII (ex: CPF, RG, nome)
        if not criptografado and exposto:
            nivel = NivelRisco.ALTO.value  # 2
            fatores.append("Identificador pessoal (PII) sem criptografia e com ampla exposição de acesso.")
        elif not criptografado and not exposto:
            nivel = NivelRisco.MEDIO.value  # 1
            fatores.append("Identificador pessoal (PII) sem criptografia em repouso.")
        elif criptografado and exposto:
            nivel = NivelRisco.MEDIO.value  # 1
            fatores.append("Identificador pessoal (PII) criptografado, mas com múltiplos atores.")
        else:
            nivel = NivelRisco.BAIXO.value  # 0
            fatores.append("Identificador pessoal (PII) criptografado com acesso restrito.")

    else:  # Dado geral / técnico
        if not criptografado and exposto:
            nivel = NivelRisco.MEDIO.value  # 1
            fatores.append("Dado técnico não criptografado com acesso irrestrito.")
        else:
            nivel = NivelRisco.BAIXO.value  # 0
            fatores.append("Dado técnico operacional com baixo impacto de privacidade.")

    fatores.extend(fatores_exposicao)

    if not criptografado and peso_sens >= 2:
        fatores.append("Ausência de criptografia detectada (Art. 46 LGPD).")

    return {
        "id_metadado": str(item.get("id")) if item.get("id") else None,
        "origem": origem,
        "sensibilidade": rotulo_sens,
        "criptografado": criptografado,
        "atores_com_acesso": atores,
        "nivel_risco": int(nivel),
        "fatores": fatores,
    }


def gerar_recomendacao_acao(nivel_geral: int, detalhes: List[Dict[str, Any]]) -> str:
    """
    Gera a ação recomendada correspondente com base no nível de risco consolidado
    e nos fatores identificados nos metadados analisados.
    """
    possui_descriptografado = any(
        not d["criptografado"] and d["sensibilidade"] in ("SENSÍVEL_SAÚDE", "PII_IDENTIFICADOR")
        for d in detalhes
    )
    possui_exposicao_atores = any(
        len(d["atores_com_acesso"]) > 3 or any(
            _contem(str(a), ATORES_NAO_CLINICOS)
            for a in d["atores_com_acesso"]
        )
        for d in detalhes
    )

    acoes: List[str] = []

    if nivel_geral == NivelRisco.CRITICO.value:
        acoes.append("URGENTE: Criptografar imediatamente os dados sensíveis de saúde (Art. 11 LGPD).")
        if possui_exposicao_atores:
            acoes.append("Revogar o acesso de atores não-clínicos ou terceiros à base de prontuários.")
        acoes.append("Manter log de acesso individualizado e auditoria em tempo real.")

    elif nivel_geral == NivelRisco.ALTO.value:
        if possui_descriptografado:
            acoes.append("Criptografar dados pessoais e identificadores em repouso e em trânsito (Art. 46 LGPD).")
        if possui_exposicao_atores:
            acoes.append("Remover acesso de perfis excedentes e aplicar princípio do privilégio mínimo.")
        acoes.append("Manter trilha de auditoria e registro estrito de visualização de registros.")

    elif nivel_geral == NivelRisco.MEDIO.value:
        if possui_descriptografado:
            acoes.append("Adotar criptografia como medida preventiva de segurança da informação.")
        acoes.append("Revisar periodicamente lista de atores autorizados e manter log de acesso.")

    else:  # BAIXO
        acoes.append("Manter log de acesso ativo e conduzir revisões periódicas de conformidade.")

    return " ".join(acoes)


def calcular_matriz_lote(metadados: List[Dict[str, Any]]) -> Tuple[int, str, List[Dict[str, Any]]]:
    """
    Executa o cálculo síncrono da Matriz de Risco para um lote completo de metadados.

    Retorna:
        Tuple[int, str, List[Dict[str, Any]]]:
          - nivel_risco_consolidado (0: BAIXO, 1: MEDIO, 2: ALTO, 3: CRITICO)
          - recomendacao_acao
          - lista_de_detalhes_por_item
    """
    if not metadados:
        nivel_baixo = NivelRisco.BAIXO.value
        return (
            nivel_baixo,
            "Lote sem metadados. Manter log de acesso ativo para monitoramento contínuo.",
            [],
        )

    detalhes = [calcular_risco_metadado(m) for m in metadados]

    # Regra do pior caso: o risco do lote é determinado pelo metadado mais vulnerável
    nivel_consolidado = max(d["nivel_risco"] for d in detalhes)
    recomendacao = gerar_recomendacao_acao(nivel_consolidado, detalhes)

    return nivel_consolidado, recomendacao, detalhes
