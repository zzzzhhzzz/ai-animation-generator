"""
分镜编写 Agent - 将脚本转换为分镜
"""

from typing import Dict, Any, List, Optional
from llm.factory import create_llm
from validators import StoryboardValidator


class StoryboardWriter:
    """分镜编写 Agent"""

    SYSTEM_PROMPT = """你是一个专业的分镜脚本作家。你擅长将视频脚本转化为详细的分镜脚本。

分镜要求：
1. 画面描述：每个画面要展示什么
2. 字幕：简洁有力，不超过20字，配合视觉
3. 读白：详细的口语化配音内容
4. 动画时序：画面元素的出场顺序和时间
5. 配音情感：读白应该用什么情感（热情/平和/强调/引导/鼓励）

## 输出格式示例：

### 示例（数学题）
```json
{
  "基本信息": {
    "标题": "勾股定理证明",
    "类型": "教学",
    "时长预估": "约3分钟",
    "目标受众": "初中生"
  },
  "分镜设计": [
    {
      "幕号": 1,
      "幕名": "开场",
      "画面描述": "显示标题",
      "字幕": "勾股定理",
      "读白": "大家好，今天我们来学习勾股定理。",
      "动画时序": "0.0s 标题出现",
      "配音情感": "热情"
    }
  ],
  "音频生成清单": [
    {"幕号": 1, "文件名": "audio_001_开场.wav", "读白文本": "大家好，今天我们来学习勾股定理。"}
  ]
}
```

重要规则：
1. 字幕必须 ≤20 字
2. 读白必须 ≥5 字
3. 每幕必须有画面描述、字幕、读白
4. 音频清单必须完整
5. 幕号必须从1开始连续编号

## 自检清单（输出前检查）：
- [ ] 基本信息是否完整（标题、类型、时长预估）？
- [ ] 字幕是否 ≤20 字？
- [ ] 读白是否 ≥5 字？
- [ ] 每幕是否都有画面描述、字幕、读白？
- [ ] 音频清单是否与分镜数量一致？
- [ ] 幕号是否从1开始连续？
- [ ] JSON 格式是否正确？

如果有任何一项不满足，请修正后再输出。"""

    def __init__(self, provider: str = "openai", **kwargs):
        self.llm = create_llm(provider, **kwargs)
        self.validator = StoryboardValidator()

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

    def write(self, script: str,
              title: str = None,
              duration_hint: str = "约1分钟",
              target_audience: str = "学生",
              style: str = "教学") -> Dict[str, Any]:
        """生成分镜

        Args:
            script: 视频脚本
            title: 视频标题
            duration_hint: 时长提示
            target_audience: 目标受众
            style: 风格

        Returns:
            分镜内容
        """
        prompt = f"""请将以下视频脚本转化为分镜脚本：

视频脚本：
{script}

基本信息：
- 标题：{title or "自动生成"}
- 时长预估：{duration_hint}
- 目标受众：{target_audience}
- 风格：{style}

请按格式输出完整的分镜脚本，确保：
1. 幕数根据内容需要安排（一般3-6幕）
2. 每幕有时长规划
3. 字幕简洁，20字以内
4. 读白口语化
5. 动画时序合理

直接输出分镜内容，不需要其他说明。"""

        try:
            # 使用带重试的调用，验证失败会自动修复
            result = self.llm.chat_with_retry(
                prompt,
                task_difficulty="medium",
                system_prompt=self.SYSTEM_PROMPT,
                validator=self._validate_output,
                fix_prompt_template="请修复以下分镜输出中的错误：\n\n原始输出：\n{original_response}\n\n错误列表：\n{error}\n\n请修正以上问题并重新输出。确保：\n1. 输出格式为 JSON\n2. 包含基本信息、分镜设计、音频生成清单\n3. 字幕 ≤20 字，读白 ≥5 字\n4. 幕号从1开始连续\n\n直接输出修正后的 JSON，不要有其他说明。",
                max_tokens=3000
            )

            if result["success"]:
                return {
                    "success": True,
                    "storyboard": result["response"],
                    "title": title,
                    "duration_hint": duration_hint,
                    "target_audience": target_audience,
                    "style": style,
                    "attempts": result.get("attempts", 1)
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "分镜验证失败"),
                    "storyboard": result.get("response", ""),
                    "attempts": result.get("attempts", 1)
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"分镜生成失败: {e}"
            }

    def write_from_math(self, math_analysis: str, html_content: str = "",
                        duration_hint: str = "约2分钟") -> Dict[str, Any]:
        """从数学分析生成辅导视频分镜（步骤3）

        Args:
            math_analysis: 数学分析结果
            html_content: HTML 可视化内容（可选）
            duration_hint: 时长提示

        Returns:
            分镜内容
        """
        prompt = f"""请根据以下数学分析生成一个详细的教学视频分镜脚本：

数学分析：
{math_analysis}

HTML可视化参考：
{html_content[:1000] if html_content else "无"}

时长：{duration_hint}

## 分镜脚本格式要求

请按以下格式输出完整的分镜脚本：

```markdown
# 分镜脚本 - {{题目名称}}

## 分镜设计

### 第1幕：{{幕名}}
**画面**: ...
**字幕**: ...（简洁，≤20字）
**读白**: ...（详细，口语化）
**动画**: ...（使用以下约定标记退场：
  - 0.0s: 字幕"xxx"淡入
  - 2.0s: → 字幕退场（用→表示退场）
  - 或：持续3秒 → 自动退场）
**目的**: ...

---

## 音频生成清单（时长列步骤5填写）

| 幕号 | 文件名 | 读白文本 | 时长 | 说话人 | 情感 |
|------|--------|----------|------|--------|------|
| 1 | audio_001_{{幕名}}.wav | "读白文本" | | xiaoxiao | 热情 |
```

## 重要规则

1. **不限制幕数** - 根据内容需要决定幕数（一般3-8幕）
2. **字幕退场约定** - 使用 "→" 或 "退场:" 标记文字退场时机
3. **配音提到什么就高亮什么** - 读白中提到的几何元素需要高亮
4. **画面时长 >= 音频时长** - 确保音画同步
5. **文件名格式**: audio_{三位幕号}_{幕名}.wav

## 分镜内容指导

1. **开场**: 引入题目，展示已知条件
2. **画图**: 根据分析画出几何图形
3. **分析**: 逐步推导，展示几何关系
4. **证明**: 详细证明过程
5. **总结**: 结论回顾

请直接输出分镜脚本内容，不要有其他说明。"""

        try:
            result = self.llm.chat_with_retry(
                prompt,
                task_difficulty="medium",
                system_prompt=self.SYSTEM_PROMPT,
                validator=self._validate_output,
                fix_prompt_template="请修复以下分镜输出中的错误：\n\n原始输出：\n{original_response}\n\n错误列表：\n{error}\n\n请修正以上问题并重新输出。确保：\n1. 包含分镜设计和音频生成清单\n2. 字幕 ≤20 字，读白详细\n3. 幕号从1开始连续\n4. 使用→标记字幕退场\n\n直接输出修正后的内容，不要有其他说明。",
                max_tokens=4000
            )

            if result["success"]:
                return {
                    "success": True,
                    "storyboard": result["response"],
                    "attempts": result.get("attempts", 1)
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "分镜验证失败"),
                    "storyboard": result.get("response", ""),
                    "attempts": result.get("attempts", 1)
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"分镜生成失败: {e}"
            }

    def write_simple(self, requirement: str,
                    duration_hint: str = "约1分钟") -> Dict[str, Any]:
        """从需求直接生成分镜（跳过脚本步骤）

        Args:
            requirement: 用户需求
            duration_hint: 时长提示

        Returns:
            分镜内容
        """
        prompt = f"""请根据以下需求直接生成一个完整的分镜脚本：

需求：{requirement}
时长：{duration_hint}

请直接输出完整的分镜脚本，包括基本信息、分镜设计和音频清单。

直接输出，不要有其他说明。"""

        try:
            # 使用带重试的调用，验证失败会自动修复
            result = self.llm.chat_with_retry(
                prompt,
                task_difficulty="medium",
                system_prompt=self.SYSTEM_PROMPT,
                validator=self._validate_output,
                fix_prompt_template="请修复以下分镜输出中的错误：\n\n原始输出：\n{original_response}\n\n错误列表：\n{error}\n\n请修正以上问题并重新输出。确保：\n1. 输出格式为 JSON\n2. 包含基本信息、分镜设计、音频生成清单\n3. 字幕 ≤20 字，读白 ≥5 字\n4. 幕号从1开始连续\n\n直接输出修正后的 JSON，不要有其他说明。",
                max_tokens=3000
            )

            if result["success"]:
                return {
                    "success": True,
                    "storyboard": result["response"],
                    "duration_hint": duration_hint,
                    "attempts": result.get("attempts", 1)
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "分镜验证失败"),
                    "storyboard": result.get("response", ""),
                    "attempts": result.get("attempts", 1)
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"分镜生成失败: {e}"
            }
