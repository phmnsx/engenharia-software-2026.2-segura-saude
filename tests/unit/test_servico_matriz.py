from unittest.mock import MagicMock, patch
import pytest

from api.servico_matriz import calcular_e_salvar


def test_calcular_e_salvar_lote_inexistente():
    with patch("api.servico_matriz.get_connection") as mock_get_conn:
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        # Simula lote não encontrado
        mock_cur.fetchone.return_value = None

        resultado = calcular_e_salvar("lote-inexistente")
        assert resultado is None


def test_calcular_e_salvar_lote_com_sucesso():
    with patch("api.servico_matriz.get_connection") as mock_get_conn, \
         patch("api.servico_matriz.send_system_log") as mock_log:
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        # 1o fetchone: lote
        lote_mock = {"id": "lote-123", "nome_lote": "Lote Teste"}
        # 2o fetchall: metadados
        metadados_mock = [
            {
                "origem": "tabela_a",
                "tipo_dado": "CPF",
                "categoria": "Identificador",
                "criptografado": True,
                "atores_com_acesso": '["medico"]',
            }
        ]
        # 3o fetchone: matriz_row retornada pelo insert
        matriz_mock = {
            "id": "matriz-123",
            "id_lote": "lote-123",
            "nivel_risco": 0,
            "recomendacao_acao": "Manter log",
            "detalhes": "[]",
            "data_hora": "2026-11-22T00:00:00Z",
        }

        mock_cur.fetchone.side_effect = [lote_mock, matriz_mock]
        mock_cur.fetchall.return_value = metadados_mock

        resultado = calcular_e_salvar("lote-123")
        assert resultado is not None
        assert resultado["id"] == "matriz-123"
        assert resultado["nivel_risco"] == 0
        assert mock_conn.commit.called
        assert mock_log.called
