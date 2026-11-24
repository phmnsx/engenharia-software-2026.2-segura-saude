import os, aio_pika, logging

logger = logging.getLogger(__name__)

class RabbitMQConnection:
    """
    Classe responsável por gerenciar a conexão do RabbitMQ, deve haver apenas uma dessas
    por container (Singleton)
    """
    _instance = None
    _connection = None
    _channel = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RabbitMQConnection, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.host = os.getenv("RABBITMQ_HOST", "localhost")
        self.port = int(os.getenv("RABBITMQ_PORT", 5672))
        self.user = os.getenv("RABBITMQ_USER", "guest")
        self.password = os.getenv("RABBITMQ_PASS", "guest")
        # Faz o URL no formato amqp 
        self.amqp_url = f"amqp://{self.user}:{self.password}@{self.host}:{self.port}/"

    async def connect(self) -> bool:
        """
        Cria conexão com o rabbitmq
        Retorna True se a conexão foi feita com sucesso
        Retorna False se houver erro
        """
        if self._connection is None or self._connection.is_closed:
            try:
                logger.info(f"Tentando conectar ao RabbitMQ em {self.host}:{self.port}...")

                self._connection = await aio_pika.connect_robust(self.amqp_url)
                self._channel = await self._connection.channel()

                await self._channel.set_qos(prefetch_count=10)
                success = True
            except Exception as e:
                logger.error(f"Falha ao conectar: {e}")
                raise

    async def get_channel(self):
        """Retorna um canal ativo, se não existir, cria um novo"""
        if self._connection is None or self._connection.is_closed:
            await self.connect()
        return self._channel

    async def close(self):
        """Fecha a conexão usado no shutdown da API."""
        if self._connection and not self._connection.is_closed:
            logger.info("Fechando conexão com o RabbitMQ...")
            await self._connection.close()
            self._connection = None
            self._channel = None
