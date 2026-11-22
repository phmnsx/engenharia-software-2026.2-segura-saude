from unittest.mock import MagicMock, patch
from api.schemas import LoteMetadadosIn, MetadadosIn
from api.controlador_metadados import _persistir_lote


def test_persistir_lote_com_metadados_chama_calculo_e_trata_erro():
    payload = LoteMetadadosIn(
        nome_lote="Lote Teste",
        base_legal="Consentimento",
        metadados=[
            MetadadosIn(
                origem="tabela_x",
                temporalidade="5 anos",
                crm_responsavel="CRM-123",
                tipo_dado="CPF",
                categoria="Identificador",
                base_legal="Consentimento",
                criptografado=True,
                atores_com_acesso=[],
            )
        ],
    )

    with patch("api.controlador_metadados.get_connection") as mock_conn, \
         patch("api.controlador_metadados.send_system_log") as mock_log, \
         patch("api.controlador_metadados.calcular_e_salvar") as mock_calc:

        mock_cur = MagicMock()
        mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = {
            "id": "lote-1",
            "nome_lote": "Lote Teste",
            "base_legal": "Consentimento",
            "analista_responsavel": None,
            "data_criacao": "2026-11-22T00:00:00Z",
        }

        # Simula erro no cálculo para verificar que não interrompe a criação do lote
        mock_calc.side_effect = RuntimeError("Erro simulado no cálculo")

        resultado = _persistir_lote(payload)

        assert resultado["id"] == "lote-1"
        assert mock_calc.called
        # Log ERROR deve ser enviado para o log_service
        error_logs = [call for call in mock_log.call_args_list if call.kwargs.get("level") == "ERROR"]
        assert len(error_logs) == 1
        assert "Falha ao calcular matriz automaticamente" in error_logs[0].kwargs.get("message")
