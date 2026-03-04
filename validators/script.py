"""
脚本验证器 - 验证视频脚本质量
"""

import json
import re
from typing import Any, Dict, List, Optional
from .base import BaseValidator, ValidationResult


class ScriptValidator(BaseValidator):
    """视频脚本验证器"""

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["标题", "类型", "内容"],
            "properties": {
                "标题": {"type": "string", "minLength": 1},
                "类型": {"type": "string", "enum": ["科普", "教学", "故事", "宣传"]},
                "时长": {"type": "string"},
                "目标受众": {"type": "string"},
                "内容": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["段落"],
                        "properties": {
                            "段落": {"type": "string", "minLength": 10},
                            "要点": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            }
        }

    def extract_output(self, text: str) -> Optional[Dict[str, Any]]:
        """从文本中提取脚本数据"""
        # 尝试从 JSON 格式提取
        json_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试从 markdown 格式提取
        return self._parse_markdown(text)

    def _parse_markdown(self, text: str) -> Optional[Dict[str, Any]]:
        """从 markdown 格式提取脚本数据"""
        data = {
            "标题": "",
            "类型": "",
            "内容": []
        }

        # 提取标题
        title_pattern = r"(?:^|\n)#\s*(.+?)(?:\n|$)"
        title_match = re.search(title_pattern, text)
        if title_match:
            data["标题"] = title_match.group(1).strip()

        # 提取类型
        type_pattern = r"[-类型type：:]\s*(.+?)(?:\n|$)"
        type_match = re.search(type_pattern, text)
        if type_match:
            data["类型"] = type_match.group(1).strip()

        # 提取内容段落
        content_sections = re.split(r"\n##+\s*|\n\d+[.、]\s*", text)
        for section in content_sections:
            section = section.strip()
            if len(section) >= 10:
                data["内容"].append({
                    "段落": section[:200],  # 截取前200字符
                    "要点": []
                })

        return data if data["内容"] else None

    def _validate_business_rules(self, data: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """验证脚本业务规则"""
        errors = []
        warnings = []

        # 验证标题
        title = data.get("标题", "")
        if not title:
            errors.append("缺少标题")
        elif len(title) > 50:
            warnings.append(f"标题较长: {len(title)}字")

        # 验证类型
        script_type = data.get("类型", "")
        valid_types = ["科普", "教学", "故事", "宣传"]
        if script_type and script_type not in valid_types:
            warnings.append(f"类型建议: {', '.join(valid_types)}")

        # 验证内容
        content = data.get("内容", [])
        if not content:
            errors.append("内容为空")
        else:
            total_length = sum(len(p.get("段落", "")) for p in content)
            if total_length < 50:
                warnings.append(f"内容较少: {total_length}字")
            if len(content) < 2:
                warnings.append("建议至少有2个段落")

        return errors, warnings

    def get_few_shot_examples(self) -> str:
        return """
## 输出格式示例：

```json
{
  "标题": "勾股定理证明",
  "类型": "教学",
  "时长": "约3分钟",
  "目标受众": "初中生",
  "内容": [
    {
      "段落": "今天我们来学习勾股定理。勾股定理是几何学中非常重要的定理...",
      "要点": ["引入勾股定理", "说明重要性"]
    },
    {
      "段落": "勾股定理指出：在直角三角形中，两条直角边的平方和等于斜边的平方...",
      "要点": ["定理表述", "公式说明"]
    }
  ]
}
```

重要规则：
1. 标题简洁明了
2. 类型为科普/教学/故事/宣传之一
3. 每个段落至少10字
4. 内容逻辑清晰"""

    def get_self_check_prompt(self) -> str:
        return """
## 自检清单（输出前检查）：
- [ ] 标题是否存在且简洁？
- [ ] 类型是否为科普/教学/故事/宣传？
- [ ] 内容是否有至少2个段落？
- [ ] 每个段落是否足够详细（≥10字）？
- [ ] JSON 格式是否正确？

如果有任何一项不满足，请修正后再输出。"""
