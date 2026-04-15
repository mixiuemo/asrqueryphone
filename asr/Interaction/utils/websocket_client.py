import asyncio
import threading
import time
import json
import os
import configparser
import socketio
from utils.loggeruitls import Logger
from utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException, RetryWithBackoff


config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../etc/config.ini'))
config = configparser.ConfigParser()
config.read(config_path, encoding='utf-8')
log = Logger()

class WebSocketClient:
    def __init__(self):
        self.socket_uri1 = config.get('System', 'SOCKETIP1')
        self.socket_uri2 = config.get('System', 'SOCKETIP2')
        
        self.sio1 = socketio.Client()
        self.sio2 = socketio.Client()
        
        self.connected1 = False
        self.connected2 = False
        
        self.connect_lock = threading.Lock()
        self.connect_thread = None
        
        # 新增：熔断器和重试机制
        self.circuit_breaker1 = CircuitBreaker(
            failure_threshold=3,    # 连续失败3次后熔断
            recovery_timeout=30,    # 30秒后尝试恢复
            expected_exception=Exception
        )
        self.circuit_breaker2 = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30,
            expected_exception=Exception
        )
        self.retry_mechanism = RetryWithBackoff(
            max_retries=2,         # 最多重试2次
            base_delay=1.0,        # 基础延迟1秒
            max_delay=10.0,        # 最大延迟10秒
            backoff_multiplier=2.0 # 指数退避
        )
        
        self._setup_callbacks()
        
    def _setup_callbacks(self):
        self.sio1.on('connect', lambda: self._on_connect(1))
        self.sio1.on('disconnect', lambda: self._on_disconnect(1))
        self.sio1.on('error', lambda error: self._on_error(error, 1))
        
        self.sio2.on('connect', lambda: self._on_connect(2))
        self.sio2.on('disconnect', lambda: self._on_disconnect(2))
        self.sio2.on('error', lambda error: self._on_error(error, 2))
        
    def _on_connect(self, socket_num):
        if socket_num == 1:
            self.connected1 = True
            log.info(f"已连接到Socket.IO服务器1: {self.socket_uri1}")
        else:
            self.connected2 = True
            log.info(f"已连接到Socket.IO服务器2: {self.socket_uri2}")
        
    def _on_disconnect(self, socket_num):
        if socket_num == 1:
            self.connected1 = False
            log.info("与Socket.IO服务器1断开连接")
        else:
            self.connected2 = False
            log.info("与Socket.IO服务器2断开连接")
        
    def _on_error(self, error, socket_num):
        log.error(f"Socket.IO服务器{socket_num}错误: {error}")
    
    def connect(self):
        """改进的连接方法，使用熔断器防止无限重试"""
        success1 = self._connect_server1()
        success2 = self._connect_server2()
        
        if not success1 and not success2:
            log.warning("两个WebSocket服务器都连接失败，进入降级模式")
            # 不再无限重试，而是等待下次调用时再尝试
        elif success1 or success2:
            log.info(f"WebSocket连接状态: 服务器1={'成功' if success1 else '失败'}, 服务器2={'成功' if success2 else '失败'}")
    
    def _connect_server1(self) -> bool:
        """连接服务器1，使用熔断器保护"""
        if self.connected1:
            return True
            
        try:
            self.circuit_breaker1.call(self._do_connect_server1)
            return True
        except CircuitBreakerOpenException as e:
            log.warning(f"服务器1熔断器开启: {e}")
            return False
        except Exception as e:
            log.error(f"连接Socket.IO服务器1失败: {e}")
            return False
    
    def _connect_server2(self) -> bool:
        """连接服务器2，使用熔断器保护"""
        if self.connected2:
            return True
            
        try:
            self.circuit_breaker2.call(self._do_connect_server2)
            return True
        except CircuitBreakerOpenException as e:
            log.warning(f"服务器2熔断器开启: {e}")
            return False
        except Exception as e:
            log.error(f"连接Socket.IO服务器2失败: {e}")
            return False
    
    def _do_connect_server1(self):
        """实际的服务器1连接逻辑"""
        self.sio1.connect(self.socket_uri1)
        self.connected1 = True
    
    def _do_connect_server2(self):
        """实际的服务器2连接逻辑"""
        self.sio2.connect(self.socket_uri2)
        self.connected2 = True
    
    def reconnect(self):
        """改进的重连方法，避免无限循环"""
        log.info("开始重连WebSocket服务器...")
        
        # 安全断开现有连接
        self._safe_disconnect()
        
        # 重置连接状态
        self.connected1 = False
        self.connected2 = False
        
        # 尝试重新连接（熔断器会控制重试频率）
        self.connect()
    
    def _safe_disconnect(self):
        """安全断开所有连接"""
        try:
            if self.sio1.connected:
                self.sio1.disconnect()
        except Exception as e:
            log.warning(f"断开服务器1连接时出错: {e}")
            
        try:
            if self.sio2.connected:
                self.sio2.disconnect()
        except Exception as e:
            log.warning(f"断开服务器2连接时出错: {e}")
    
    def ensure_connection(self):
        with self.connect_lock:
            if (not self.connected1 or not self.connected2) and not self.connect_thread:
                def start_connection():
                    self.connect()
                
                self.connect_thread = threading.Thread(target=start_connection, daemon=True)
                self.connect_thread.start()
    
    async def send_message(self, user_circuit: str, user_message: str, system_message: str):
        if not self.connected1 and not self.connected2:
            log.warning("Socket.IO未连接，无法发送消息")
            return False
            
        success_count = 0
        data = {
            "user_circuit": user_circuit,
            "user_message": user_message,
            "system_message": system_message
        }
        
        if self.connected1:
            try:
                self.sio1.emit('ai114_message', data)
                log.info(f"Socket.IO消息发送成功到服务器1: 电路号={user_circuit}")
                success_count += 1
            except Exception as e:
                log.error(f"发送Socket.IO消息到服务器1失败: {e}")
        
        if self.connected2:
            try:
                self.sio2.emit('ai114_message', data)
                log.info(f"Socket.IO消息发送成功到服务器2: 电路号={user_circuit}")
                success_count += 1
            except Exception as e:
                log.error(f"发送Socket.IO消息到服务器2失败: {e}")
        
        return success_count > 0
            
    def send_message_sync(self, user_circuit: str, user_message: str, system_message: str):
        """改进的同步消息发送，使用重试机制"""
        data = {
            "user_circuit": user_circuit,
            "user_message": user_message,
            "system_message": system_message
        }
        
        try:
            # 使用重试机制发送消息
            return self.retry_mechanism.execute(self._send_message_internal, data, user_circuit)
        except Exception as e:
            log.error(f"消息发送最终失败: {e}")
            return False
    
    def _send_message_internal(self, data: dict, user_circuit: str) -> bool:
        """内部消息发送逻辑"""
        # 确保至少有一个连接可用
        if not self.connected1 and not self.connected2:
            self.ensure_connection()
            # 给连接一点时间建立
            for _ in range(5):
                if self.connected1 or self.connected2:
                    break
                time.sleep(0.2)
            
            if not self.connected1 and not self.connected2:
                raise Exception("所有WebSocket连接都不可用")
        
        success_count = 0
        
        # 尝试通过服务器1发送
        if self.connected1:
            try:
                self.sio1.emit('ai114_message', data)
                log.info(f"Socket.IO消息发送成功到服务器1: 电路号={user_circuit}")
                success_count += 1
            except Exception as e:
                log.error(f"发送Socket.IO消息到服务器1失败: {e}")
                self.connected1 = False  # 标记连接失效
        
        # 尝试通过服务器2发送
        if self.connected2:
            try:
                self.sio2.emit('ai114_message', data)
                log.info(f"Socket.IO消息发送成功到服务器2: 电路号={user_circuit}")
                success_count += 1
            except Exception as e:
                log.error(f"发送Socket.IO消息到服务器2失败: {e}")
                self.connected2 = False  # 标记连接失效
        
        if success_count == 0:
            raise Exception("消息发送到所有服务器都失败")
        
        return True
    
    def get_connection_status(self) -> dict:
        """获取连接状态和熔断器信息"""
        return {
            "server1": {
                "connected": self.connected1,
                "circuit_breaker": self.circuit_breaker1.get_state()
            },
            "server2": {
                "connected": self.connected2,
                "circuit_breaker": self.circuit_breaker2.get_state()
            }
        }
    
    def reset_circuit_breakers(self):
        """手动重置所有熔断器（用于运维）"""
        self.circuit_breaker1.reset()
        self.circuit_breaker2.reset()
        log.info("所有熔断器已手动重置")

websocket_client = WebSocketClient() 