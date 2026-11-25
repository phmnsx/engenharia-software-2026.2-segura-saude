import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
    async def test_nao_deve_abrir_duas_conexoes_se_ja_conectado(self, mock_connect):
        # Cria um MagicMock (síncrono) para a conexão
        mock_connection = MagicMock()
        # Garante que a propriedade is_closed retorna False (Conexão aberta)
        mock_connection.is_closed = False 
        
        # O channel também precisa ser um AsyncMock
        mock_connection.channel = AsyncMock() 
        
        mock_connect.return_value = mock_connection
    
        conn = RabbitMQConnection()
        await conn.connect()
        await conn.connect() # Chama o connect de novo
    
        # Assert: O connect_robust só deve ter sido chamado 1 vez (Singleton)
        mock_connect.assert_called_once()
        
    @patch("aio_pika.connect_robust", new_callable=AsyncMock)
    async def test_nao_deve_abrir_duas_conexoes_se_ja_conectado(self, mock_connect):
        mock_connect.return_value = AsyncMock()
        
        conn = RabbitMQConnection()
        await conn.connect()
        await conn.connect() # Chama o connect de novo

        # Assert: O connect_robust só deve ter sido chamado 1 vez (Singleton)
        mock_connect.assert_called_once()