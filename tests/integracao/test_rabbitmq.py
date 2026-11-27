import json
import pytest
import asyncio
import aio_pika
import os
from src.common.rabbitmqconfig.publisher import RabbitMQPublisher
from src.common.rabbitmqconfig.connection import RabbitMQConnection

FILA_TESTE = "fila_teste_integracao"

@pytest.mark.asyncio
class TestRabbitMQIntegration:

    def setup_method(self):
        RabbitMQConnection._instance = None
        RabbitMQConnection._connection = None
        RabbitMQConnection._channel = None

    @pytest.mark.skipif(
        "CI" not in os.environ and "RABBITMQ_HOST" not in os.environ,
        reason="Requer um RabbitMQ rodando localmente ou no CI"
    )
    async def test_deve_publicar_e_consumir_mensagem(self):
        """
        Testa o fluxo completo: Produtor -> Fila -> Consumidor.
        """
        conn_manager = RabbitMQConnection()
        publisher = RabbitMQPublisher()
        
        try:
            # 1. Garante que a conexão está aberta
            channel = await conn_manager.get_channel()
            
            # 2. Declara a fila de teste
            queue = await channel.declare_queue(FILA_TESTE, durable=True)
            
            # 3. Esvazia a fila caso tenha lixo de testes anteriores
            await queue.purge()

            # 4. Publica a mensagem
            payload = {"status": "teste_ok", "id": 123}
            await publisher._ack_publish(FILA_TESTE, payload)

            # 5. Consome a mensagem (com timeout de 3s para não travar o teste)
            async with queue.iterator(timeout=3) as q:
                async for message in q:
                    async with message.process():
                        dados_recebidos = json.loads(message.body.decode())
                        break # Sai do loop após pegar a primeira mensagem

            # 6. Verifica se a mensagem recebida é igual à enviada
            assert dados_recebidos["data"] == payload
            
        finally:
            # Limpeza: Apaga a fila e fecha a conexão
            if conn_manager._channel:
                await conn_manager._channel.queue_delete(FILA_TESTE)
            await conn_manager.close()