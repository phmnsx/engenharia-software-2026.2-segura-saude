import pytest
from unittest.mock import AsyncMock, patch
from src.common.rabbitmqconfig.connection import RabbitMQConnection

# O pytest-asyncio precisa desse marcador para testes async
@pytest.mark.asyncio
class TestRabbitMQConnectionUnit:

    def setup_method(self):
        # Limpa a instância Singleton antes de cada teste
        RabbitMQConnection._instance = None
        RabbitMQConnection._connection = None
        RabbitMQConnection._channel = None

    @patch("aio_pika.connect_robust", new_callable=AsyncMock)
    async def test_deve_conectar_ao_rabbitmq(self, mock_connect):
        # Arrange (Prepara o mock)
        mock_connection = AsyncMock()
        mock_connection.is_closed = False
        mock_channel = AsyncMock()
        mock_connection.channel.return_value = mock_channel
        mock_connect.return_value = mock_connection

        conn = RabbitMQConnection()

        # Act (Executa)
        await conn.connect()

        # Assert (Verifica)
        mock_connect.assert_called_once() # O connect_robust foi chamado?
        mock_connection.channel.assert_called_once() # O canal foi aberto?
        assert conn._connection is not None
        assert conn._channel == mock_channel

    @patch("aio_pika.connect_robust", new_callable=AsyncMock)
    async def test_nao_deve_abrir_duas_conexoes_se_ja_conectado(self, mock_connect):
        mock_connect.return_value = AsyncMock()
        
        conn = RabbitMQConnection()
        await conn.connect()
        await conn.connect() # Chama o connect de novo

        # Assert: O connect_robust só deve ter sido chamado 1 vez (Singleton)
        mock_connect.assert_called_once()