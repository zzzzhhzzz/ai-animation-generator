"""
脚本编写 Agent - 根据需求生成视频脚本
"""

from typing import Dict, Any, Optional
from llm.factory import create_llm
from validators import ScriptValidator


class ScriptWriter:
    """脚本编写 Agent"""

    SYSTEM_PROMPT = """你是一个专业的视频脚本作家。你擅长将各种主题转化为生动有趣的视频脚本。
你的任务是根据给定的需求，生成一个完整的视频脚本。

脚本要求：
1. 结构清晰：有开场、内容、结尾
2. 内容充实：每个部分都要有足够的细节
3. 口语化：读白要自然流畅，像在和人对话
4. 时长合理：总时长控制在需求范围内

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
4. 内容逻辑清晰

## 自检清单（输出前检查）：
- [ ] 标题是否存在且简洁？
- [ ] 类型是否为科普/教学/故事/宣传？
- [ ] 内容是否有至少2个段落？
- [ ] 每个段落是否足够详细（≥10字）？
- [ ] JSON 格式是否正确？

如果有任何一项不满足，请修正后再输出。"""

    def __init__(self, provider: str = "openai", **kwargs):
        self.llm = create_llm(provider, **kwargs)
        self.validator = ScriptValidator()

    def _validate_output(self, output: str) -> tuple[bool, str]:
        """验证输出

        Args:
            output: LLM 原始输出

        Returns:
            (is_valid, error_message)
        """
        result = self.validator.validate(output)
        if result.is_valid:
            return True, ""
        return False, ", ".join(result.errors)

    def write(self, requirement: str,
              title: str = None,
              duration_hint: str = "1-2分钟",
              style: str = "教学") -> Dict[str, Any]:
        """生成视频脚本

        Args:
            requirement: 用户需求描述
            title: 视频标题（可选）
            duration_hint: 时长提示
            style: 风格（教学/科普/故事/宣传）

        Returns:
            脚本内容
        """
        prompt = f"""请根据以下需求生成一个视频脚本：

需求：{requirement}

标题：{title or "根据需求自动生成"}
时长：{duration_hint}
风格：{style}

请生成完整的视频脚本，包括：
1. 视频标题
2. 整体结构
3. 每部分的详细内容（开场白、讲解、总结等）

直接输出脚本内容。"""

        try:
            # 使用带重试的调用，验证失败会自动修复
            result = self.llm.chat_with_retry(
                prompt,
                task_difficulty="medium",
                system_prompt=self.SYSTEM_PROMPT,
                validator=self._validate_output,
                fix_prompt_template="请修复以下视频脚本中的错误：\n\n原始输出：\n{original_response}\n\n错误列表：\n{error}\n\n请修正以上问题并重新输出。确保：\n1. 输出格式为 JSON\n2. 包含标题、类型、内容\n3. 内容至少有2个段落\n4. 每个段落至少10字\n\n直接输出修正后的 JSON，不要有其他说明。",
                max_tokens=2000
            )

            if result["success"]:
                return {
                    "success": True,
                    "script": result["response"],
                    "title": title,
                    "duration_hint": duration_hint,
                    "style": style,
                    "attempts": result.get("attempts", 1)
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "脚本验证失败"),
                    "script": result.get("response", ""),
                    "attempts": result.get("attempts", 1)
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"脚本生成失败: {e}"
            }

    def write_from_analysis(self, analysis_result: Dict[str, Any],
                          duration_hint: str = "1-2分钟") -> Dict[str, Any]:
        """从图片分析结果生成脚本

        Args:
            analysis_result: ImageAnalyzer 的分析结果
            duration_hint: 时长提示

        Returns:
            脚本内容
        """
        if not analysis_result.get("success"):
            return {
                "success": False,
                "error": "分析结果无效"
            }

        analysis = analysis_result.get("analysis", "")
        return self.write(
            requirement=f"请基于以下内容制作视频：\n\n{analysis}",
            duration_hint=duration_hint
        )
