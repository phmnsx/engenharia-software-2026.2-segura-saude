import json
import logging
import uuid
from datetime import datetime

import aio_pika

from common.outbox.models.outbox import OutboxMessage

from .connection import RabbitMQConnection

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    def __init__(self):
        self.conn_manager = RabbitMQConnection()

    async def ack_publish(self, fila: str, mensagem: dict):
        """
        Método interno auxiliar para garantir o Publisher Confirms.
        """
        try:
            channel = await self.conn_manager.get_channel()
            await channel.declare_queue(fila, durable=True)

            payload = {
                "id_msg": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "data": mensagem,
            }
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=fila,
            )
            logger.info(f"[RabbitMQ] Mensagem publicada na fila '{fila}' com sucesso.")
        except Exception as e:
            logger.error(f"[RabbitMQ] Falha ao publicar na fila '{fila}': {e}")
            raise

    async def create_log_msg(self, usuario: str, acao: str, detalhes: dict = None):
        """Método específico para o serviço de logs (ASR01)."""
        return OutboxMessage(
            queue_name="logs_auditoria_queue",
            payload={
                "usuario": usuario,
                "acao": acao,
                "detalhes": detalhes or {},
            }
        )
    
    async def publicar_tarefa_matriz(self, id_lote: str, id_matriz: str):
        """Método específico para solicitar o cálculo assíncrono da matriz (ASR06)."""
        return OutboxMessage(
            queue_name="matriz_calculo_queue",
            payload={
                "id_lote": id_lote,
                "id_matriz": id_matriz,
                "status": "PENDENTE",
            }
        )

    async def publicar_lote_metadados(self, lote_payload: dict):
        """Publica um lote de metadados para persistência assíncrona no serviço de matriz/metadados."""
        fila = "metadados_ingestao_queue"
        await self.ack_publish(fila, lote_payload)
