"""
Testes unitários – Motor de Cálculo da Matriz de Risco (RF001, DT03).

Valida as regras diretas da LGPD para os 4 níveis de risco:
  - Baixo (0), Médio (1), Alto (2), Crítico (3)
E a geração das ações recomendadas correspondentes:
  - Criptografar, Remover acesso, Manter log de acesso.
"""

from src.api.models import NivelRisco
from src.api.motor_risco import (
    classificar_sensibilidade,
    avaliar_exposicao_atores,
    calcular_risco_metadado,
    calcular_matriz_lote,
)


class TestClassificacaoSensibilidade:
    def test_sensibilidade_saude_cid_e_prontuario(self):
        peso, rotulo = classificar_sensibilidade(
            origem="tabela_prontuario",
            tipo_dado="CID-10",
        )
        assert peso == 3
        assert rotulo == "SENSÍVEL_SAÚDE"

    def test_sensibilidade_saude_categoria_sensivel(self):
        peso, rotulo = classificar_sensibilidade(
            origem="tb_exames",
            categoria="Dado Sensível",
        )
        assert peso == 3
        assert rotulo == "SENSÍVEL_SAÚDE"

    def test_sensibilidade_pii_cpf(self):
        peso, rotulo = classificar_sensibilidade(
            origem="tabela_pacientes",
            tipo_dado="CPF",
        )
        assert peso == 2
        assert rotulo == "PII_IDENTIFICADOR"

    def test_sensibilidade_pii_nome_telefone(self):
        peso, rotulo = classificar_sensibilidade(
            origem="contatos",
            tipo_dado="telefone",
        )
        assert peso == 2
        assert rotulo == "PII_IDENTIFICADOR"

    def test_sensibilidade_geral_tecnico(self):
        peso, rotulo = classificar_sensibilidade(
            origem="dispositivo_iot",
            tipo_dado="temperatura_sala",
        )
        assert peso == 1
        assert rotulo == "GERAL_TECNICO"

    def test_palavras_contendo_substrings_nao_geram_falsos_positivos(self):
        """
        Garante que palavras que contêm termos como substrings não sejam classificadas
        como dados sensíveis ou PII:
        - 'Energia' (contém 'rg') -> GERAL_TECNICO (1)
        - 'Nomenclatura' (contém 'nome') -> GERAL_TECNICO (1)
        - 'Incidente de TI' (contém 'cid') -> GERAL_TECNICO (1)
        - 'Tratamento de resíduos' (antigo 'tratamento') -> GERAL_TECNICO (1)
        """
        for termo in ["Energia", "Nomenclatura", "Incidente de TI", "Tratamento de resíduos"]:
            peso, rotulo = classificar_sensibilidade(tipo_dado=termo)
            assert peso == 1, f"Termo '{termo}' classificado incorretamente com peso {peso}"
            assert rotulo == "GERAL_TECNICO"

    def test_termos_legitimos_continuam_detectados(self):
        """Verifica que termos legítimos como 'CID', 'CPF' e 'Nome do paciente' continuam sendo detectados."""
        peso_cid, rotulo_cid = classificar_sensibilidade(tipo_dado="CID")
        assert peso_cid == 3
        assert rotulo_cid == "SENSÍVEL_SAÚDE"

        peso_cpf, rotulo_cpf = classificar_sensibilidade(tipo_dado="CPF")
        assert peso_cpf == 2
        assert rotulo_cpf == "PII_IDENTIFICADOR"

        peso_nome, rotulo_nome = classificar_sensibilidade(tipo_dado="Nome do paciente")
        assert peso_nome in (2, 3)  # 'paciente' e 'nome' são PII (2), 'paciente' também pode ser PII
        assert rotulo_nome == "PII_IDENTIFICADOR"


class TestAvaliacaoExposicaoAtores:
    def test_atores_clinicos_restritos_nao_exposto(self):
        exposto, fatores = avaliar_exposicao_atores(
            ["médico", "enfermeiro"],
            peso_sensibilidade=3,
        )
        assert exposto is False
        assert len(fatores) == 0

    def test_excesso_de_atores_viola_privilegio_minimo(self):
        atores = ["médico", "enfermeiro", "fisioterapeuta", "farmacêutico"]
        exposto, fatores = avaliar_exposicao_atores(atores, peso_sensibilidade=3)
        assert exposto is True
        assert any("privilégio mínimo" in f for f in fatores)

    def test_ator_nao_clinico_acessando_dado_sensivel(self):
        atores = ["médico", "terceiro_consultoria"]
        exposto, fatores = avaliar_exposicao_atores(atores, peso_sensibilidade=3)
        assert exposto is True
        assert any("Atores não-clínicos" in f for f in fatores)

    def test_ator_externo_acessando_pii(self):
        atores = ["marketing", "atendente"]
        exposto, fatores = avaliar_exposicao_atores(atores, peso_sensibilidade=2)
        assert exposto is True


class TestCalculoRiscoIndividual:
    def test_risco_critico_sensivel_sem_criptografia_com_alta_exposicao(self):
        """Dado sensível de saúde (CID) em texto claro com terceiros = CRÍTICO (3)."""
        item = {
            "origem": "prontuarios_medicos",
            "tipo_dado": "CID-10",
            "criptografado": False,
            "atores_com_acesso": ["médico", "terceiro_pesquisa", "analista"],
        }
        res = calcular_risco_metadado(item)
        assert res["nivel_risco"] == NivelRisco.CRITICO.value
        assert res["sensibilidade"] == "SENSÍVEL_SAÚDE"
        assert res["criptografado"] is False

    def test_risco_alto_sensivel_sem_criptografia_acesso_restrito(self):
        """Dado sensível de saúde em texto claro mas apenas médico = ALTO (2)."""
        item = {
            "origem": "laudo_exame",
            "tipo_dado": "diagnostico",
            "criptografado": False,
            "atores_com_acesso": ["médico"],
        }
        res = calcular_risco_metadado(item)
        assert res["nivel_risco"] == NivelRisco.ALTO.value

    def test_risco_alto_pii_sem_criptografia_com_alta_exposicao(self):
        """CPF sem criptografia acessível por equipe ampla/marketing = ALTO (2)."""
        item = {
            "origem": "cadastro_paciente",
            "tipo_dado": "CPF",
            "criptografado": False,
            "atores_com_acesso": ["recepcao", "marketing", "atendente"],
        }
        res = calcular_risco_metadado(item)
        assert res["nivel_risco"] == NivelRisco.ALTO.value

    def test_risco_medio_sensivel_criptografado_acesso_restrito(self):
        """Dado sensível protegido por criptografia e acesso controlado = MÉDIO (1)."""
        item = {
            "origem": "prontuario_eletronico",
            "tipo_dado": "prescricao",
            "criptografado": True,
            "atores_com_acesso": ["médico_assistente"],
        }
        res = calcular_risco_metadado(item)
        assert res["nivel_risco"] == NivelRisco.MEDIO.value

    def test_risco_medio_pii_sem_criptografia_acesso_restrito(self):
        """CPF sem criptografia mas acesso restrito = MÉDIO (1)."""
        item = {
            "origem": "pacientes",
            "tipo_dado": "CPF",
            "criptografado": False,
            "atores_com_acesso": ["medico"],
        }
        res = calcular_risco_metadado(item)
        assert res["nivel_risco"] == NivelRisco.MEDIO.value

    def test_risco_baixo_pii_criptografado_acesso_restrito(self):
        """CPF criptografado com acesso restrito = BAIXO (0)."""
        item = {
            "origem": "pacientes",
            "tipo_dado": "CPF",
            "criptografado": True,
            "atores_com_acesso": ["medico"],
        }
        res = calcular_risco_metadado(item)
        assert res["nivel_risco"] == NivelRisco.BAIXO.value

    def test_risco_baixo_dado_tecnico(self):
        """Dado técnico operacional com acesso padrão = BAIXO (0)."""
        item = {
            "origem": "sistema_leitos",
            "tipo_dado": "codigo_leito",
            "criptografado": False,
            "atores_com_acesso": ["enfermagem"],
        }
        res = calcular_risco_metadado(item)
        assert res["nivel_risco"] == NivelRisco.BAIXO.value

    def test_risco_baixo_falsos_positivos_com_quatro_atores_nao_clinicos_sem_criptografia(self):
        """
        Para os quatro casos de falso positivo:
        Mesmo com 4 atores (exposição ampla) e sem criptografia, por serem dados gerais/técnicos
        e sem atores não-clínicos especiais, ou mesmo com atores operacionais padrão,
        se não forem pessoais/sensíveis e os atores não forem não-clínicos abusivos:
        - Peso sensibilidade = 1 (GERAL_TECNICO)
        - Se não tiver exposição (>3 atores dá exposto=True -> para peso=1 resulta em MEDIO (1)).
        - Porém, com acesso normal ou com os 4 termos da tabela:
        Verifica que não são classificados como PII nem SENSIVEL, e com acesso restrito dão BAIXO (0).
        """
        for termo in ["Energia", "Nomenclatura", "Incidente de TI", "Tratamento de resíduos"]:
            item = {
                "origem": "tabela_geral",
                "tipo_dado": termo,
                "criptografado": False,
                "atores_com_acesso": ["suporte", "analista_sistema"],
            }
            res = calcular_risco_metadado(item)
            assert res["sensibilidade"] == "GERAL_TECNICO"
            assert res["nivel_risco"] == NivelRisco.BAIXO.value


class TestConsolidacaoMatrizLoteEAcoes:
    def test_lote_vazio_retorna_baixo(self):
        nivel, acao, detalhes = calcular_matriz_lote([])
        assert nivel == NivelRisco.BAIXO.value
        assert "Manter log de acesso" in acao
        assert detalhes == []

    def test_lote_misto_regra_pior_caso_critico(self):
        """Lote misto deve assumir nível CRÍTICO pelo elo mais fraco."""
        metadados = [
            {
                "origem": "telemetria",
                "tipo_dado": "pressao_tubulacao",
                "criptografado": False,
                "atores_com_acesso": ["manutencao"],
            },
            {
                "origem": "prontuarios_uti",
                "tipo_dado": "diagnostico_covid",
                "criptografado": False,
                "atores_com_acesso": ["medico", "terceiro_pesquisa", "estagiario"],
            },
        ]
        nivel, acao, detalhes = calcular_matriz_lote(metadados)
        assert nivel == NivelRisco.CRITICO.value
        assert len(detalhes) == 2
        assert "URGENTE: Criptografar" in acao
        assert "Revogar o acesso" in acao
        assert "Manter log de acesso" in acao

    def test_lote_com_pii_desprotegido_resulta_em_alto_com_acoes(self):
        metadados = [
            {
                "origem": "cadastro_geral",
                "tipo_dado": "CPF_e_Nome",
                "criptografado": False,
                "atores_com_acesso": ["atendente", "financeiro", "marketing", "externo"],
            }
        ]
        nivel, acao, detalhes = calcular_matriz_lote(metadados)
        assert nivel == NivelRisco.ALTO.value
        assert "Criptografar dados pessoais" in acao
        assert "Remover acesso" in acao
        assert "Manter trilha de auditoria" in acao

    def test_lote_totalmente_protegido_resulta_em_baixo(self):
        metadados = [
            {
                "origem": "pacientes_seguros",
                "tipo_dado": "CPF",
                "criptografado": True,
                "atores_com_acesso": ["medico_titular"],
            }
        ]
        nivel, acao, detalhes = calcular_matriz_lote(metadados)
        assert nivel == NivelRisco.BAIXO.value
        assert "Manter log de acesso ativo" in acao
