import asyncio
import json
import logging

import aio_pika

from .connection import RabbitMQConnection

logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    def __init__(self):
        self.conn_manager = RabbitMQConnection()

    async def _processar_mensagem(self, message: aio_pika.IncomingMessage, callback):
        """
        Método interno que gerencia o ciclo de vida da mensagem (ACK/NACK).
        """
        async with message.process(requeue=False, ignore_processed=True):
            try:
                payload = json.loads(message.body.decode())
                logger.info(f"[RabbitMQ] Mensagem recebida: {payload}")

                await callback(payload)

                logger.info("[RabbitMQ] Mensagem processada com sucesso (ACK enviado).")
            except json.JSONDecodeError:
                logger.error("[RabbitMQ] Erro: Mensagem não é um JSON válido. Descartando (NACK).")
                raise
            except Exception as e:
                logger.error(
                    f"[RabbitMQ] Erro ao processar a mensagem: {e}. "
                    "Devolvendo para a fila (NACK + requeue)."
                )
                await message.nack(requeue=True)
                raise

    async def _iniciar_consumo(self, callback, fila:str):
        while True:
            try:
                logger.info(f"[RabbitMQ] Tentando conectar e ouvir a fila '{fila}'...")
                channel = await self.conn_manager.get_channel()
                
                # Declara a fila (garante que ela exista no broker)
                queue = await channel.declare_queue(fila, durable=True)

                logger.info(f"[RabbitMQ] Ouvindo a fila '{fila}'...")
                
                # O consume retorna imediatamente. 
                # O await asyncio.Future() mantém a função rodando e escutando.
                await queue.consume(
                    lambda message: self._processar_mensagem(message, callback),
                    no_ack=False,
                )
                # Mantém o worker vivo até a conexão cair
                await asyncio.Future() 
                
            except asyncio.CancelledError:
                logger.info("[RabbitMQ] Consumidor cancelado pelo sistema.")
                break
            except Exception as e:
                logger.error(f"[RabbitMQ] Conexão perdida com a fila '{fila}': {e}")
                logger.info("[RabbitMQ] Tentando reconectar em 5 segundos...")
                # Espera 5 segundos antes de tentar conectar de novo
                await asyncio.sleep(5)

    async def iniciar_consumo_logs(self, callback):
        """Consome a fila de auditoria (ASR01). Usado pelo Worker de Logs."""
        fila = "logs_auditoria_queue"
        await self._iniciar_consumo(callback, fila)
        

    async def iniciar_consumo_matriz(self, callback):
        """Consome a fila de cálculo de matriz (ASR06). Usado pelo Worker de Matriz."""
        fila = "matriz_calculo_queue"
        await self._iniciar_consumo(callback, fila)

    async def iniciar_consumo_metadados(self, callback):
        """Consome a fila de ingestão de lotes de metadados."""
        fila = "metadados_ingestao_queue"
        await self._iniciar_consumo(callback, fila)
