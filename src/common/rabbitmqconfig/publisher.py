import aio_pika, json, logging, uuid
from connection import RabbitMQConnection
from datetime import datetime

logger = logging.getLogger(__name__)

class RabbitMQPublisher:
    def __init__(self):
        self.conn_manager = RabbitMQConnection()

    async def _ack_publish(self, fila: str, mensagem: dict):
        """
        Método interno auxiliar para garantir o Publisher Confirms
        """
        try:
            channel = await self.conn_manager.get_channel()
            await channel.declare_queue(fila, durable=True)

            payload = {
                "id_msg" : str(uuid.uuid4()),
                "timestamp" : datetime.now().isoformat(),
                "data" : mensagem
            }

            async with channel.transaction():
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(payload).encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                    ),
                    routing_key=fila
                )
            logger.info(f"[RabbitMQ] Mensagem publicada na fila '{fila}' com sucesso.")
        except Exception as e:
            logger.error(f"[RabbitMQ] Falha ao publicar na fila '{fila}': {e}")
            raise

    
