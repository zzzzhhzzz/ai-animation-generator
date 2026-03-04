"""
验证器基类 - 定义验证接口和通用验证逻辑
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from abc import ABC, abstractmethod


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    fixed_output: Optional[str] = None

    def __bool__(self):
        return self.is_valid


class ValidationError(Exception):
    """验证错误异常"""
    def __init__(self, message: str, errors: List[str] = None):
        super().__init__(message)
        self.errors = errors or []


class BaseValidator(ABC):
    """验证器基类"""

    # 默认重试次数
    DEFAULT_MAX_RETRIES = 3

    # 指数退避初始延迟（秒）
    INITIAL_BACKOFF = 1.0

    # 最大退避延迟（秒）
    MAX_BACKOFF = 10.0

    def __init__(self, max_retries: int = DEFAULT_MAX_RETRIES):
        self.max_retries = max_retries

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """返回验证 Schema"""
        pass

    @abstractmethod
    def extract_output(self, text: str) -> Optional[Dict[str, Any]]:
        """从 LLM 输出中提取结构化数据"""
        pass

    def validate(self, output: str) -> ValidationResult:
        """验证输出是否符合 Schema

        Args:
            output: LLM 原始输出

        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []

        # 1. 尝试解析 JSON
        try:
            data = self.extract_output(output)
            if data is None:
                errors.append("无法从输出中提取结构化数据")
                return ValidationResult(is_valid=False, errors=errors)
        except Exception as e:
            errors.append(f"JSON 解析失败: {e}")
            return ValidationResult(is_valid=False, errors=errors)

        # 2. Schema 验证
        schema_errors = self._validate_schema(data, self.get_schema())
        errors.extend(schema_errors)

        # 3. 业务规则验证
        rule_errors, rule_warnings = self._validate_business_rules(data)
        errors.extend(rule_errors)
        warnings.extend(rule_warnings)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """验证数据是否符合 Schema"""
        errors = []

        # 验证必需字段
        required = schema.get("required", [])
        for field_name in required:
            if field_name not in data:
                errors.append(f"缺少必需字段: {field_name}")

        # 验证属性
        properties = schema.get("properties", {})
        for field_name, field_schema in properties.items():
            if field_name in data:
                field_errors = self._validate_field(
                    field_name, data[field_name], field_schema
                )
                errors.extend(field_errors)

        return errors

    def _validate_field(self, field_name: str, value: Any, schema: Dict[str, Any]) -> List[str]:
        """验证单个字段"""
        errors = []

        # 类型检查
        expected_type = schema.get("type")
        if expected_type and not self._check_type(value, expected_type):
            errors.append(f"字段 {field_name} 类型错误: 期望 {expected_type}")

        # 枚举检查
        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"字段 {field_name} 值不在允许范围内: {value}")

        # 字符串长度检查
        if isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                errors.append(f"字段 {field_name} 长度不足: {len(value)} < {schema['minLength']}")
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                errors.append(f"字段 {field_name} 长度超限: {len(value)} > {schema['maxLength']}")
            if "pattern" in schema:
                pattern = re.compile(schema["pattern"])
                if not pattern.match(value):
                    errors.append(f"字段 {field_name} 格式不匹配: {value}")

        # 数组检查
        if isinstance(value, list):
            if "items" in schema:
                for i, item in enumerate(value):
                    item_errors = self._validate_field(
                        f"{field_name}[{i}]", item, schema["items"]
                    )
                    errors.extend(item_errors)

        # 对象检查
        if isinstance(value, dict) and "properties" in schema:
            for sub_field, sub_schema in schema["properties"].items():
                if sub_field in value:
                    sub_errors = self._validate_field(
                        f"{field_name}.{sub_field}", value[sub_field], sub_schema
                    )
                    errors.extend(sub_errors)

        return errors

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """检查类型"""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected = type_map.get(expected_type)
        if expected is None:
            return True
        return isinstance(value, expected)

    def _validate_business_rules(self, data: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """验证业务规则 - 子类可重写"""
        return [], []

    def validate_and_fix(self, output: str, llm_callable: Callable[[str], str]) -> ValidationResult:
        """验证并尝试修复输出

        Args:
            output: LLM 原始输出
            llm_callable: 用于修复的 LLM 调用函数

        Returns:
            ValidationResult: 最终验证结果
        """
        for attempt in range(self.max_retries):
            result = self.validate(output)

            if result.is_valid:
                return result

            # 尝试修复
            if attempt < self.max_retries - 1:
                fix_prompt = self._generate_fix_prompt(output, result.errors)
                output = llm_callable(fix_prompt)
            else:
                # 最后一次尝试，标记为失败
                pass

        # 所有重试都失败
        return ValidationResult(
            is_valid=False,
            errors=result.errors,
            warnings=result.warnings
        )

    def _generate_fix_prompt(self, output: str, errors: List[str]) -> str:
        """生成修复提示"""
        return f"""请修复以下输出中的错误：

原始输出：
{output}

错误列表：
{chr(10).join(f"- {e}" for e in errors)}

请修正以上问题并重新输出。确保：
1. 输出格式正确
2. 所有必需字段都存在
3. 字段值在有效范围内

直接输出修正后的内容，不要有其他说明。"""

    def get_few_shot_examples(self) -> str:
        """返回 few-shot 示例 - 子类可重写"""
        return ""

    def get_self_check_prompt(self) -> str:
        """返回自检提示 - 子类可重写"""
        return """
## 自检清单（输出前检查）：
- [ ] 输出格式是否正确？
- [ ] 所有必需字段是否都存在？
- [ ] 字段值是否在有效范围内？

如果有任何一项不满足，请修正后再输出。"""
