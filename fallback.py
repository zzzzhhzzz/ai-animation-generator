"""
降级处理模块 - 当高级策略失败时使用更保守的策略
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class Strategy:
    """策略配置"""
    name: str
    difficulty: str
    description: str
    model: Optional[str] = None
    max_retries: int = 3


@dataclass
class FallbackResult:
    """降级处理结果"""
    success: bool
    result: Any = None
    error: Optional[str] = None
    strategy_used: Optional[str] = None
    attempts: int = 0
    fallback_history: List[Dict[str, str]] = field(default_factory=list)


class FallbackHandler:
    """降级处理器
    当高级策略失败时，自动尝试更保守的策略
    """

    # 默认策略列表（从高级到低级）
    DEFAULT_STRATEGIES = [
        Strategy("gpt-4-turbo", "hard", "最强模型", max_retries=3),
        Strategy("gpt-4o", "medium", "中等模型", max_retries=2),
        Strategy("gpt-4o-mini", "simple", "简单模型", max_retries=2),
    ]

    def __init__(self, strategies: Optional[List[Strategy]] = None,
                 use_templates: bool = True):
        """初始化降级处理器

        Args:
            strategies: 自定义策略列表
            use_templates: 是否在所有策略失败时使用模板
        """
        self.strategies = strategies or self.DEFAULT_STRATEGIES
        self.use_templates = use_templates
        self._template_registry: Dict[str, str] = {}

    def register_template(self, task_type: str, template: str):
        """注册模板

        Args:
            task_type: 任务类型
            template: 模板内容
        """
        self._template_registry[task_type] = template

    def execute(self,
                task: str,
                task_type: str,
                llm_callable: Callable[[str, str], str],
                validator: Optional[Callable[[Any], tuple[bool, str]]] = None,
                max_strategies: Optional[int] = None) -> FallbackResult:
        """执行带降级的任务

        Args:
            task: 任务描述
            task_type: 任务类型（用于模板匹配）
            llm_callable: LLM 调用函数，签名为 (prompt, difficulty) -> response
            validator: 可选的验证函数，签名为 (response) -> (is_valid, error_message)
            max_strategies: 最大尝试的策略数量

        Returns:
            FallbackResult: 执行结果
        """
        result = FallbackResult(success=False)
        strategies_to_try = self.strategies[:max_strategies] if max_strategies else self.strategies
        fallback_history = []

        for i, strategy in enumerate(strategies_to_try):
            logger.info(f"尝试策略 {i+1}/{len(strategies_to_try)}: {strategy.name} ({strategy.description})")

            try:
                # 调用 LLM
                response = llm_callable(task, strategy.difficulty)

                # 如果有验证器，验证输出
                if validator is not None:
                    is_valid, error_msg = validator(response)

                    if not is_valid:
                        logger.warning(f"策略 {strategy.name} 验证失败: {error_msg}")
                        fallback_history.append({
                            "strategy": strategy.name,
                            "status": "validation_failed",
                            "error": error_msg
                        })
                        continue

                # 成功
                result.success = True
                result.result = response
                result.strategy_used = strategy.name
                result.attempts = i + 1
                result.fallback_history = fallback_history
                return result

            except Exception as e:
                logger.warning(f"策略 {strategy.name} 执行失败: {e}")
                fallback_history.append({
                    "strategy": strategy.name,
                    "status": "error",
                    "error": str(e)
                })
                continue

        # 所有策略都失败，尝试使用模板
        if self.use_templates and task_type in self._template_registry:
            logger.info(f"所有策略失败，尝试使用模板: {task_type}")
            template = self._template_registry[task_type]

            try:
                # 使用模板填充任务
                template_result = self._apply_template(template, task)

                result.success = True
                result.result = template_result
                result.strategy_used = "template"
                result.attempts = len(strategies_to_try) + 1
                result.fallback_history = fallback_history
                return result

            except Exception as e:
                logger.error(f"模板执行失败: {e}")
                fallback_history.append({
                    "strategy": "template",
                    "status": "error",
                    "error": str(e)
                })

        # 完全失败
        result.error = f"所有 {len(strategies_to_try)} 个策略都失败"
        if self.use_templates:
            result.error += f"，且无可用模板"
        result.fallback_history = fallback_history
        return result

    def _apply_template(self, template: str, task: str) -> str:
        """应用模板"""
        # 简单的模板填充
        return template.format(task=task)


class RetryHandler:
    """重试处理器 - 带指数退避的重试机制"""

    def __init__(self,
                 max_retries: int = 3,
                 initial_backoff: float = 1.0,
                 max_backoff: float = 10.0,
                 backoff_factor: float = 2.0):
        """初始化重试处理器

        Args:
            max_retries: 最大重试次数
            initial_backoff: 初始退避时间（秒）
            max_backoff: 最大退避时间（秒）
            backoff_factor: 退避因子
        """
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_factor = backoff_factor

    def calculate_backoff(self, attempt: int) -> float:
        """计算退避时间"""
        import time
        backoff = self.initial_backoff * (self.backoff_factor ** attempt)
        return min(backoff, self.max_backoff)

    def execute(self,
                func: Callable[[], Any],
                validator: Optional[Callable[[Any], tuple[bool, str]]] = None,
                on_retry: Optional[Callable[[int, str], None]] = None) -> Dict[str, Any]:
        """执行带重试的任务

        Args:
            func: 要执行的函数
            validator: 可选的验证函数
            on_retry: 可选的重试回调

        Returns:
            包含 success、result、error、attempts 的字典
        """
        import time

        last_error = None

        for attempt in range(self.max_retries):
            try:
                result = func()

                # 如果有验证器，验证结果
                if validator is not None:
                    is_valid, error_msg = validator(result)

                    if not is_valid:
                        logger.warning(f"验证失败 (尝试 {attempt + 1}/{self.max_retries}): {error_msg}")

                        if attempt < self.max_retries - 1:
                            if on_retry:
                                on_retry(attempt + 1, error_msg)

                            backoff_time = self.calculate_backoff(attempt)
                            logger.info(f"等待 {backoff_time:.1f} 秒后重试...")
                            time.sleep(backoff_time)
                        continue

                return {
                    "success": True,
                    "result": result,
                    "attempts": attempt + 1
                }

            except Exception as e:
                last_error = str(e)
                logger.warning(f"执行失败 (尝试 {attempt + 1}/{self.max_retries}): {last_error}")

                if attempt < self.max_retries - 1:
                    if on_retry:
                        on_retry(attempt + 1, last_error)

                    backoff_time = self.calculate_backoff(attempt)
                    logger.info(f"等待 {backoff_time:.1f} 秒后重试...")
                    time.sleep(backoff_time)

        # 所有重试都失败
        return {
            "success": False,
            "error": f"达到最大重试次数 ({self.max_retries}): {last_error}",
            "attempts": self.max_retries
        }
