import asyncio
from api.db import SessionLocal
from api.models.outbox import OutboxMessage
from common.rabbitmqconfig.publisher import RabbitMQPublisher

async def processar_outbox():
    print("[WORKER] Worker do Outbox iniciado...")
    publisher = RabbitMQPublisher()
    
    while True:
        try:

            with SessionLocal() as db:
                # with_for_update(skip_locked=True) evita que os 3 gateways peguem a mesma mensagem
                mensagens = (
                    db.query(OutboxMessage)
                    .filter(OutboxMessage.status == "PENDENTE")
                    .with_for_update(skip_locked=True) # <-- A MÁGICA ACONTECE AQUI
                    .limit(10)
                    .all()
                )
                
                # muda o status para PROCESSANDO para indicar que este Gateway "pegou" a mensagem
                for msg in mensagens:
                    msg.status = "PROCESSANDO"
                db.commit()

                mensagens_para_enviar = [(m.id, m.queue_name, m.payload) for m in mensagens]

            for msg_id, queue_name, payload in mensagens_para_enviar:
                try:
                    await publisher.ack_publish(queue_name, payload)
                    
                    with SessionLocal() as db:
                        msg = db.query(OutboxMessage).get(msg_id)
                        msg.status = "ENVIADO"
                        db.commit()
                        
                except Exception as e:
                    print(f"[OUTBOX] Falha ao enviar {msg_id}. Voltando para PENDENTE. {e}")
                    # Se falhou (RabbitMQ offline), devolve para PENDENTE
                    with SessionLocal() as db:
                        msg = db.query(OutboxMessage).get(msg_id)
                        msg.status = "PENDENTE"
                        db.commit()
                        
        except Exception as e:
            print(f"[OUTBOX] Erro no worker: {e}")
            
        await asyncio.sleep(5)