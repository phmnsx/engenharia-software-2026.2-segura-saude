import pytest
from pydantic import ValidationError
from src.api.models import Metadados, LoteMetadados, MatrizDeRisco, NivelRisco


def test_metadados_criacao_basica():
    m = Metadados(origem="tabela_pacientes", temporalidade="5 anos", crm_responsavel="CRM-SE-12345")
    assert m.id is not None
    assert m.criptografado is False
    assert m.atores_com_acesso == []


def test_metadados_campos_opcionais_ausentes():
    m = Metadados(origem="tabela_consultas", temporalidade="10 anos", crm_responsavel="CRM-SE-99999")
    assert m.tipo_dado is None
    assert m.categoria is None
    assert m.base_legal is None


def test_metadados_com_todos_campos():
    m = Metadados(
        origem="tabela_exames",
        temporalidade="20 anos",
        crm_responsavel="CRM-SE-11111",
        tipo_dado="VARCHAR(10)",
        categoria="Sensível",
        base_legal="Legítimo Interesse",
        criptografado=True,
        atores_com_acesso=["médico", "analista"],
    )
    assert m.base_legal == "Legítimo Interesse"
    assert len(m.atores_com_acesso) == 2
    assert m.criptografado is True


def test_metadados_sem_campos_obrigatorios_falha():
    with pytest.raises(ValidationError):
        Metadados(tipo_dado="VARCHAR(11)")


def test_metadados_ids_unicos():
    m1 = Metadados(origem="tabela_a", temporalidade="1 ano", crm_responsavel="CRM-SE-00001")
    m2 = Metadados(origem="tabela_b", temporalidade="1 ano", crm_responsavel="CRM-SE-00002")
    assert m1.id != m2.id


def test_lote_metadados_criacao_basica():
    lote = LoteMetadados(nome_lote="Lote Sintético A", base_legal="Consentimento")
    assert lote.id is not None
    assert lote.metadados == []
    assert lote.data_criacao is not None


def test_lote_metadados_agrega_metadados():
    m1 = Metadados(origem="tabela_pacientes", temporalidade="5 anos", crm_responsavel="CRM-SE-11111")
    m2 = Metadados(origem="tabela_consultas", temporalidade="10 anos", crm_responsavel="CRM-SE-22222")
    lote = LoteMetadados(
        nome_lote="Lote Sintético B",
        base_legal="Consentimento",
        metadados=[m1, m2],
    )
    assert len(lote.metadados) == 2
    assert lote.base_legal == "Consentimento"


def test_lote_sem_base_legal_falha():
    with pytest.raises(ValidationError):
        LoteMetadados(nome_lote="Sem Base Legal")


def test_lote_ids_diferentes():
    l1 = LoteMetadados(nome_lote="A", base_legal="Consentimento")
    l2 = LoteMetadados(nome_lote="B", base_legal="Consentimento")
    assert l1.id != l2.id


def test_matriz_de_risco_criacao():
    lote = LoteMetadados(nome_lote="Lote Sintético C", base_legal="Consentimento")
    matriz = MatrizDeRisco(
        id_lote=lote.id,
        nivel_risco=NivelRisco.ALTO,
        recomendacao_acao="Criptografar dado antes de armazenar",
    )
    assert matriz.nivel_risco == NivelRisco.ALTO
    assert matriz.id_lote == lote.id
    assert matriz.data_hora is not None


def test_nivel_risco_valores_int():
    assert NivelRisco.BAIXO == 0
    assert NivelRisco.MEDIO == 1
    assert NivelRisco.ALTO == 2
    assert NivelRisco.CRITICO == 3


def test_nivel_risco_todos_validos():
    for nivel in [NivelRisco.BAIXO, NivelRisco.MEDIO, NivelRisco.ALTO, NivelRisco.CRITICO]:
        m = MatrizDeRisco(id_lote="lote-sintetico-123", nivel_risco=nivel, recomendacao_acao="ação")
        assert m.nivel_risco == nivel


def test_nivel_risco_invalido_falha():
    with pytest.raises(ValidationError):
        MatrizDeRisco(id_lote="lote-123", nivel_risco="Desconhecido", recomendacao_acao="x")
