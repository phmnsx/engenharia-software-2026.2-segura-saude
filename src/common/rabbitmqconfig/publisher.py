import aio_pika, json, logging, uuid
from src.common.rabbitmqconfig.connection import RabbitMQConnection
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

    async def publicar_log(self, usuario:str, acao:str, detalhes: dict = None):
        """Método específico para o serviço de logs (ASR01)."""
        fila = "logs_auditoria_queue"
        dados = {
            "usuario": usuario,
            "acao": acao,
            "detalhes": detalhes or {}
        }
        await self._ack_publish(fila, dados)

    async def publicar_tarefa_matriz(self, id_lote: str, id_matriz: str):
        """Método específico para solicitar o cálculo assíncrono da matriz (ASR06)."""
        fila = "matriz_calculo_queue"
        dados = {
            "id_lote": id_lote,
            "id_matriz": id_matriz,
            "status": "PENDENTE"
        }
        await self._ack_publish(fila, dados)
