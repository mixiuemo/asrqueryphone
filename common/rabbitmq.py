import pika
import sys
import os
import time
from sys_config import SysConfig
from loguru import logger

logger.remove(0)
logger = logger.opt(colors=True)
logger.add(sys.stderr, format="[<level>{level}</level>]:{time} - {message}")  

Config = SysConfig()
ExchangeName = 'AI114'

class RabbitMQ:
    def __init__(self):
        self.user = Config.get('MSG','MSG_SERVER_USER')
        self.password = Config.get(sect='MSG',item='MSG_SERVER_PASSWORD')
        self.host = Config.get(sect='MSG', item='MSG_SERVER_ADDR')
        item = Config.get(sect='MSG', item='MSG_SERVER_PORT')
        if item != None:
            self.port = int(item)
        self.connection = None
        self.channel = None
        self.connect()

    def readConf(self):
        config = SysConfig()
        self.user = config.get('MSG','MSG_SERVER_USER')
        self.password = config.get(sect='MSG',item='MSG_SERVER_PASSWORD')
        self.host = config.get(sect='MSG', item='MSG_SERVER_ADDR')
        item = config.get(sect='MSG', item='MSG_SERVER_PORT')
        if item != None:
            self.port = int(item)

    def connect(self):
        # 先关闭旧连接
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
        except:
            pass
        
        self.connection = None
        self.channel = None
        
        self.readConf()
        credentials = pika.PlainCredentials(self.user, self.password)
        parameters = pika.ConnectionParameters(host=self.host, port=self.port, credentials=credentials)
        try:
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.channel.exchange_declare(exchange=ExchangeName, exchange_type='fanout')
            logger.info(f"连接消息服务器成功{self.host}")
        except Exception as e:
            logger.error(f"连接消息队列失败: {e}")
            self.connection = None
            self.channel = None

    def close(self):
        if self.connection and not self.connection.is_closed:
            self.connection.close()

    def consume(self, callback):
        # check connection/channel state and reconnect if needed
        if not self.connection or self.connection.is_closed:
            logger.warning("连接已关闭，正在重新连接...")
            self.connect()

        if not self.channel or self.channel.is_closed:
            logger.warning("通道已关闭，正在重新连接...")
            self.connect()

        if not self.channel:
            logger.error(f"Connection is not established.")
            raise Exception("Connection is not established.")

        try:
            # default keeps old fanout behavior (each service gets a copy)
            # set MQ_CONSUME_MODE=shared for work-queue load balancing
            consume_mode = os.getenv("MQ_CONSUME_MODE", "broadcast").strip().lower()

            if consume_mode == "shared":
                queue_name = os.getenv("ASR_CONSUME_QUEUE", "asr_shared_queue")
                prefetch_count = int(os.getenv("MQ_PREFETCH", "1"))

                self.channel.queue_declare(queue=queue_name, durable=True)
                self.channel.queue_bind(exchange=ExchangeName, queue=queue_name)
                self.channel.basic_qos(prefetch_count=prefetch_count)

                def _wrapped_callback(ch, method, properties, body):
                    try:
                        callback(ch, method, properties, body)
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception as callback_error:
                        logger.error(f"处理消息失败，将重回队列: {callback_error}")
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

                self.channel.basic_consume(queue=queue_name, on_message_callback=_wrapped_callback, auto_ack=False)
            else:
                result = self.channel.queue_declare(queue="", exclusive=False, auto_delete=True)
                queue_name = result.method.queue
                self.channel.queue_bind(exchange=ExchangeName, queue=queue_name)
                self.channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"消费消息时出错: {e}")
            try:
                if self.connection and not self.connection.is_closed:
                    self.connection.close()
            except:
                pass
            time.sleep(15)
            self.connect()
            raise

    def heartbeat(self, message):
        try:
            self.channel.basic_publish(exchange=ExchangeName,
                                   routing_key='',
                                   body='HEARTBEAT:'+message,
                                   )
        except:
            self.connect()
        
    def publish(self, message):
        retry_count = 0
        # 最多重试2次
        max_retries = 2  
        
        while retry_count <= max_retries:
            if not self.channel:
                self.connect()
                
            if not self.channel:  
                retry_count += 1
                time.sleep(1)  
                continue
                
            try:
                self.channel.basic_publish(exchange=ExchangeName,
                                   routing_key='',
                                   body=message,
                                   )
                return True  # 发送成功
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                self.connect()  # 重新连接
                retry_count += 1
                
        logger.error(f"发送消息失败，已达到最大重试次数: {message}")
        return False  

