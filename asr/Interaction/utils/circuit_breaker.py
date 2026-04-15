"""
熔断器模式实现
防止网络连接问题导致系统崩溃
"""
import time
import threading
from typing import Callable, Any
from utils.loggeruitls import Logger

log = Logger()


class CircuitBreaker:
    """
    熔断器实现
    
    状态说明：
    - CLOSED: 正常状态，允许请求通过
    - OPEN: 熔断状态，拒绝所有请求
    - HALF_OPEN: 半开状态，允许少量请求测试服务是否恢复
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, expected_exception: type = Exception):
        """
        初始化熔断器
        
        Args:
            failure_threshold: 失败阈值，连续失败多少次后熔断
            recovery_timeout: 恢复超时时间（秒），熔断后多久尝试恢复
            expected_exception: 预期的异常类型，只有这种异常才计入失败
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        # 状态管理
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        # 线程安全
        self._lock = threading.Lock()
        
        log.info(f"熔断器初始化: 失败阈值={failure_threshold}, 恢复超时={recovery_timeout}s")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过熔断器调用函数
        
        Args:
            func: 要调用的函数
            *args, **kwargs: 函数参数
            
        Returns:
            函数执行结果
            
        Raises:
            CircuitBreakerOpenException: 熔断器开启时抛出
            原函数的异常: 函数执行失败时抛出
        """
        with self._lock:
            # 检查熔断器状态
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                    log.info("熔断器进入半开状态，尝试恢复")
                else:
                    raise CircuitBreakerOpenException(
                        f"熔断器开启，拒绝调用。剩余时间: {self._get_remaining_timeout():.1f}s"
                    )
        
        # 尝试执行函数
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
        except Exception as e:
            # 非预期异常不计入失败计数
            log.warning(f"熔断器: 非预期异常 {type(e).__name__}: {e}")
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置熔断器"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _get_remaining_timeout(self) -> float:
        """获取剩余的熔断时间"""
        if self.last_failure_time is None:
            return 0
        elapsed = time.time() - self.last_failure_time
        return max(0, self.recovery_timeout - elapsed)
    
    def _on_success(self):
        """成功时的处理"""
        with self._lock:
            if self.state == "HALF_OPEN":
                log.info("熔断器恢复正常，重置为CLOSED状态")
            
            self.failure_count = 0
            self.state = "CLOSED"
    
    def _on_failure(self):
        """失败时的处理"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            log.warning(f"熔断器记录失败: {self.failure_count}/{self.failure_threshold}")
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                log.error(f"熔断器开启! 连续失败{self.failure_count}次，{self.recovery_timeout}秒后尝试恢复")
    
    def get_state(self) -> dict:
        """获取熔断器当前状态信息"""
        with self._lock:
            return {
                "state": self.state,
                "failure_count": self.failure_count,
                "failure_threshold": self.failure_threshold,
                "last_failure_time": self.last_failure_time,
                "remaining_timeout": self._get_remaining_timeout() if self.state == "OPEN" else 0
            }
    
    def reset(self):
        """手动重置熔断器"""
        with self._lock:
            self.failure_count = 0
            self.last_failure_time = None
            self.state = "CLOSED"
            log.info("熔断器已手动重置")


class CircuitBreakerOpenException(Exception):
    """熔断器开启时抛出的异常"""
    pass


class RetryWithBackoff:
    """
    带退避算法的重试机制
    配合熔断器使用，提供更完善的容错能力
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0, backoff_multiplier: float = 2.0):
        """
        初始化重试配置
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            backoff_multiplier: 退避倍数
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行带重试的函数调用
        
        Args:
            func: 要执行的函数
            *args, **kwargs: 函数参数
            
        Returns:
            函数执行结果
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):  # +1 因为第一次不算重试
            try:
                return func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = min(
                        self.base_delay * (self.backoff_multiplier ** attempt),
                        self.max_delay
                    )
                    log.warning(f"第{attempt + 1}次尝试失败: {e}, {delay:.1f}秒后重试")
                    time.sleep(delay)
                else:
                    log.error(f"重试{self.max_retries}次后仍然失败: {e}")
        
        # 所有重试都失败了
        raise last_exception