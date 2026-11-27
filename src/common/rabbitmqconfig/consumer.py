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

    async def iniciar_consumo_logs(self, callback):
        """Consome a fila de auditoria (ASR01). Usado pelo Worker de Logs."""
        channel = await self.conn_manager.get_channel()
        fila = "logs_auditoria_queue"

        queue = await channel.declare_queue(fila, durable=True)

        logger.info(f"[RabbitMQ] Aguardando mensagens na fila '{fila}'...")
        await queue.consume(
            lambda message: self._processar_mensagem(message, callback),
            no_ack=False,
        )

    async def iniciar_consumo_matriz(self, callback):
        """Consome a fila de cálculo de matriz (ASR06). Usado pelo Worker de Matriz."""
        channel = await self.conn_manager.get_channel()
        fila = "matriz_calculo_queue"

        queue = await channel.declare_queue(fila, durable=True)

        logger.info(f"[RabbitMQ] Aguardando mensagens na fila '{fila}'...")
        await queue.consume(
            lambda message: self._processar_mensagem(message, callback),
            no_ack=False,
        )

    async def iniciar_consumo_metadados(self, callback):
        """Consome a fila de ingestão de lotes de metadados."""
        channel = await self.conn_manager.get_channel()
        fila = "metadados_ingestao_queue"

        queue = await channel.declare_queue(fila, durable=True)

        logger.info(f"[RabbitMQ] Aguardando mensagens na fila '{fila}'...")
        await queue.consume(
            lambda message: self._processar_mensagem(message, callback),
            no_ack=False,
        )
