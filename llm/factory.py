"""
LLM 工厂模块 - 根据任务难度选择合适的 LLM
支持重试机制和降级处理
"""

import os
import time
import logging
from typing import Optional, Callable, Any, Dict, List, Union

logger = logging.getLogger(__name__)


class LLMProvider:
    """LLM 提供商基类"""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url

    def chat(self, messages: list, model: str = "gpt-4", **kwargs) -> str:
        """发送聊天请求"""
        raise NotImplementedError

    def vision_chat(self, messages: list, model: str = "gpt-4o", **kwargs) -> str:
        """发送带图片的聊天请求"""
        raise NotImplementedError


class OpenAILLM(LLMProvider):
    """OpenAI LLM"""

    def __init__(self, api_key: str = None, base_url: str = None):
        super().__init__(api_key, base_url)
        self.client = None

    def _get_client(self):
        if self.client is None:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                print("Warning: openai package not installed")
        return self.client

    def chat(self, messages: list, model: str = "gpt-4o-mini", **kwargs) -> str:
        client = self._get_client()
        if not client:
            return "Error: OpenAI client not available"

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content

    def vision_chat(self, messages: list, model: str = "gpt-4o", **kwargs) -> str:
        return self.chat(messages, model, **kwargs)


class AnthropicLLM(LLMProvider):
    """Anthropic Claude LLM"""

    def __init__(self, api_key: str = None):
        super().__init__(api_key)
        self.client = None

    def _get_client(self):
        if self.client is None:
            try:
                import anthropic
                api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
                self.client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                print("Warning: anthropic package not installed")
        return self.client

    def chat(self, messages: list, model: str = "claude-3-haiku-20240307", **kwargs) -> str:
        client = self._get_client()
        if not client:
            return "Error: Anthropic client not available"

        # 转换消息格式
        system = ""
        filtered_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system = msg.get("content", "")
            else:
                filtered_messages.append(msg)

        response = client.messages.create(
            model=model,
            system=system,
            messages=filtered_messages,
            **kwargs
        )
        return response.content[0].text

    def vision_chat(self, messages: list, model: str = "claude-3-5-sonnet-20241022", **kwargs) -> str:
        return self.chat(messages, model, **kwargs)


class LLMWrapper:
    """LLM 包装器 - 根据配置选择提供商
    支持重试机制和降级处理
    """

    PROVIDERS = {
        "openai": OpenAILLM,
        "anthropic": AnthropicLLM,
    }

    # LLM 选择配置
    MODEL_CONFIG = {
        # 简单任务 - 快速、便宜
        "simple": {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-haiku-20240307",
        },
        # 中等任务 - 平衡
        "medium": {
            "openai": "gpt-4o",
            "anthropic": "claude-3-sonnet-20240229",
        },
        # 复杂任务 - 高能力
        "hard": {
            "openai": "gpt-4-turbo",
            "anthropic": "claude-3-5-sonnet-20241022",
        },
        # 视觉任务
        "vision": {
            "openai": "gpt-4o",
            "anthropic": "claude-3-5-sonnet-20241022",
        },
    }

    # 降级策略：从高级到低级
    FALLBACK_STRATEGIES = [
        {"difficulty": "hard", "description": "最强模型"},
        {"difficulty": "medium", "description": "中等模型"},
        {"difficulty": "simple", "description": "简单模型"},
    ]

    def __init__(self, provider: str = "openai",
                 max_retries: int = 3,
                 initial_backoff: float = 1.0,
                 max_backoff: float = 10.0,
                 **kwargs):
        """初始化 LLM 包装器

        Args:
            provider: 提供商 ("openai" 或 "anthropic")
            max_retries: 最大重试次数
            initial_backoff: 初始退避时间（秒）
            max_backoff: 最大退避时间（秒）
            **kwargs: 其他参数
        """
        provider_class = self.PROVIDERS.get(provider, OpenAILLM)
        self.provider = provider_class(**kwargs)
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff

    def _exponential_backoff(self, attempt: int) -> float:
        """计算指数退避时间

        Args:
            attempt: 当前重试次数（从0开始）

        Returns:
            退避时间（秒）
        """
        backoff = self.initial_backoff * (2 ** attempt)
        return min(backoff, self.max_backoff)

    def chat_with_retry(self, prompt: str, task_difficulty: str = "simple",
                        system_prompt: str = "You are a helpful assistant.",
                        validator: Optional[Callable[[str], bool]] = None,
                        fix_prompt_template: Optional[str] = None,
                        **kwargs) -> Dict[str, Any]:
        """带重试机制的聊天请求

        Args:
            prompt: 用户提示
            task_difficulty: 任务难度
            system_prompt: 系统提示
            validator: 可选的验证函数，验证失败时会触发重试
            fix_prompt_template: 可选的修复提示模板
            **kwargs: 其他参数

        Returns:
            包含 success、response、error、attempts 的字典
        """
        last_error = None
        current_prompt = prompt
        current_difficulty = task_difficulty

        for attempt in range(self.max_retries):
            try:
                # 根据当前难度选择模型
                model = self.MODEL_CONFIG.get(
                    current_difficulty,
                    self.MODEL_CONFIG["simple"]
                ).get(
                    self.provider.__class__.__name__.replace("LLM", "").lower(),
                    "gpt-4o-mini"
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": current_prompt}
                ]

                response = self.provider.chat(messages, model=model, **kwargs)

                # 如果有验证器，验证输出
                if validator is not None:
                    is_valid, error_msg = validator(response)
                    if not is_valid:
                        logger.warning(
                            f"验证失败 (尝试 {attempt + 1}/{self.max_retries}): {error_msg}"
                        )

                        # 如果还有重试机会，尝试修复
                        if attempt < self.max_retries - 1 and fix_prompt_template:
                            current_prompt = fix_prompt_template.format(
                                original_response=response,
                                error=error_msg
                            )
                            # 增加严格模式提示
                            current_prompt += "\n\n【严格模式】请确保输出格式正确，不要有错误。"
                            continue
                        else:
                            # 验证失败且已达最大重试次数
                            return {
                                "success": False,
                                "response": response,
                                "error": f"验证失败: {error_msg}",
                                "attempts": attempt + 1
                            }

                return {
                    "success": True,
                    "response": response,
                    "attempts": attempt + 1
                }

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"LLM 调用失败 (尝试 {attempt + 1}/{self.max_retries}): {last_error}"
                )

                # 指数退避
                if attempt < self.max_retries - 1:
                    backoff_time = self._exponential_backoff(attempt)
                    logger.info(f"等待 {backoff_time:.1f} 秒后重试...")
                    time.sleep(backoff_time)

        # 所有重试都失败
        return {
            "success": False,
            "error": f"达到最大重试次数 ({self.max_retries}): {last_error}",
            "attempts": self.max_retries
        }

    def chat_with_fallback(self, prompt: str, task_difficulty: str = "simple",
                           system_prompt: str = "You are a helpful assistant.",
                           max_strategies: int = 3,
                           **kwargs) -> Dict[str, Any]:
        """带降级策略的聊天请求

        当高级模型失败时，自动尝试更简单的模型

        Args:
            prompt: 用户提示
            task_difficulty: 初始任务难度
            system_prompt: 系统提示
            max_strategies: 最大尝试的策略数量
            **kwargs: 其他参数

        Returns:
            包含 success、response、error、strategy 的字典
        """
        # 构建策略列表
        strategies = []
        for i, strategy in enumerate(self.FALLBACK_STRATEGIES):
            if i >= max_strategies:
                break

            # 如果指定了初始难度，从该难度开始
            if task_difficulty == strategy["difficulty"]:
                strategies = self.FALLBACK_STRATEGIES[i:i+max_strategies]
                break
        else:
            # 如果没有匹配到，从第一个策略开始
            strategies = self.FALLBACK_STRATEGIES[:max_strategies]

        for strategy in strategies:
            difficulty = strategy["difficulty"]
            try:
                logger.info(f"尝试策略: {strategy['description']} ({difficulty})")

                model = self.MODEL_CONFIG.get(difficulty).get(
                    self.provider.__class__.__name__.replace("LLM", "").lower(),
                    "gpt-4o-mini"
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]

                response = self.provider.chat(messages, model=model, **kwargs)

                return {
                    "success": True,
                    "response": response,
                    "strategy": difficulty,
                    "description": strategy["description"]
                }

            except Exception as e:
                logger.warning(
                    f"策略 {strategy['description']} 失败: {e}"
                )
                continue

        # 所有策略都失败
        return {
            "success": False,
            "error": f"所有 {len(strategies)} 个策略都失败",
            "strategy": None
        }

    def chat(self, prompt: str, task_difficulty: str = "simple",
             system_prompt: str = "You are a helpful assistant.", **kwargs) -> str:
        """发送聊天请求（兼容旧接口）

        Args:
            prompt: 用户提示
            task_difficulty: 任务难度 ("simple", "medium", "hard", "vision")
            system_prompt: 系统提示
            **kwargs: 其他参数

        Returns:
            LLM 响应文本
        """
        # 尝试使用重试机制
        result = self.chat_with_retry(
            prompt=prompt,
            task_difficulty=task_difficulty,
            system_prompt=system_prompt,
            **kwargs
        )

        if result["success"]:
            return result["response"]
        else:
            # 如果重试失败，抛出异常（兼容旧接口）
            raise RuntimeError(result.get("error", "Unknown error"))

    def chat_with_messages(self, messages: list, task_difficulty: str = "simple", **kwargs) -> str:
        """使用消息列表发送请求"""
        model = self.MODEL_CONFIG.get(task_difficulty, self.MODEL_CONFIG["simple"]).get(
            self.provider.__class__.__name__.replace("LLM", "").lower(), "gpt-4o-mini"
        )
        return self.provider.chat(messages, model=model, **kwargs)


def create_llm(provider: str = "openai", model: str = None, **kwargs) -> LLMWrapper:
    """创建 LLM 实例的工厂函数

    Args:
        provider: 提供商 ("openai" 或 "anthropic")
        model: 指定模型（可选，会覆盖默认选择）
        **kwargs: 其他参数

    Returns:
        LLMWrapper 实例
    """
    llm = LLMWrapper(provider, **kwargs)
    if model:
        # 允许直接指定模型
        llm.default_model = model
    return llm
