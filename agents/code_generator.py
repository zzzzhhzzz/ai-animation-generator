"""
代码生成 Agent - 根据分镜生成 Manim 动画代码
"""

import os
import ast
from typing import Dict, Any, Optional
from llm.factory import create_llm
from validators import CodeValidator


class CodeGenerator:
    """Manim 代码生成 Agent"""

    SYSTEM_PROMPT = """你是一个专业的 Manim 动画代码工程师。你擅长根据分镜脚本生成高质量的 Manim 动画代码。

要求：
1. 代码必须完整可运行
2. 遵循 Manim 最佳实践
3. 音画同步：动画时长 >= 音频时长
4. 正确的文件路径
5. 中文字体支持
6. 美观的配色

颜色方案参考：
- 背景：#1a1a2e（深蓝）
- 主色：#4ecca3（青色）
- 辅助色：#e94560（红色）
- 高亮色：#ffc107（黄色）
- 文字：#ffffff（白色）

## 输出格式示例：

```python
from manim import *
import json
import os

class AnimationScene(Scene):
    COLORS = {
        "background": "#1a1a2e",
        "primary": "#4ecca3",
        "secondary": "#e94560",
    }

    def __init__(self):
        super().__init__()
        self.audio_dir = "audio"

    def construct(self):
        self.play_scene_1()
        self.play_scene_2()

    def play_scene_1(self):
        self.add_sound("audio/audio_001_开场.wav")
        title = Text("勾股定理", font_size=48, color=WHITE)
        self.play(FadeIn(title))
        self.wait(2)
```

重要规则：
1. 必须导入 manim
2. 必须有 Scene 类
3. 必须有 construct 方法
4. 音频路径使用 "audio/xxx.wav" 格式
5. 建议指定字体以支持中文

## 自检清单（输出前检查）：
- [ ] 是否导入了 manim？
- [ ] 是否有 Scene 类定义？
- [ ] 是否有 construct 方法？
- [ ] 音频路径格式是否正确（audio/xxx.wav）？
- [ ] Python 语法是否正确？
- [ ] 是否指定了字体（支持中文）？
- [ ] 代码是否完整可运行？

如果有任何一项不满足，请修正后再输出。"""

    def __init__(self, provider: str = "openai", **kwargs):
        self.llm = create_llm(provider, **kwargs)
        self.validator = CodeValidator()

    def _validate_output(self, output: str) -> tuple[bool, str]:
        """验证输出

        Args:
            output: LLM 原始输出

        Returns:
            (is_valid, error_message)
        """
        code = self._extract_code(output)
        result = self.validator.validate_code_syntax(code)
        if not result.is_valid:
            return False, ", ".join(result.errors)

        result = self.validator.validate_code_imports(code)
        if not result.is_valid:
            return False, ", ".join(result.errors)

        return True, ""

    def generate(self, storyboard: str,
                title: str = "Animation",
                output_path: str = "script.py") -> Dict[str, Any]:
        """生成动画代码

        Args:
            storyboard: 分镜脚本
            title: 视频标题
            output_path: 输出文件路径

        Returns:
            生成结果
        """
        prompt = f"""请根据以下分镜脚本生成 Manim 动画代码：

分镜脚本：
{storyboard}

标题：{title}

要求：
1. 生成完整的 Python 代码
2. 音频文件路径使用相对路径 "audio/xxx.wav"
3. 确保动画时长 >= 音频时长
4. 每幕开始时添加音频
5. 使用清晰的颜色方案

直接输出代码，不需要其他说明。"""

        try:
            # 使用带重试的调用，验证失败会自动修复
            result = self.llm.chat_with_retry(
                prompt,
                task_difficulty="hard",
                system_prompt=self.SYSTEM_PROMPT,
                validator=self._validate_output,
                fix_prompt_template="请修复以下 Manim 代码中的错误：\n\n原始代码：\n{original_response}\n\n错误列表：\n{error}\n\n请修正以上问题并重新输出完整代码。确保：\n1. 必须导入 manim\n2. 必须有 Scene 类\n3. 必须有 construct 方法\n4. 音频路径使用 audio/xxx.wav 格式\n5. Python 语法正确\n\n直接输出修正后的代码，不要有其他说明。",
                max_tokens=4000
            )

            if result["success"]:
                # 提取代码部分（去除可能的markdown标记）
                code = self._extract_code(result["response"])

                # 保存代码
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(code)

                return {
                    "success": True,
                    "code": code,
                    "output_path": output_path,
                    "attempts": result.get("attempts", 1)
                }
            else:
                # 即使验证失败，也尝试提取代码保存
                code = self._extract_code(result.get("response", ""))
                if code:
                    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(code)

                return {
                    "success": False,
                    "error": result.get("error", "代码验证失败"),
                    "code": code,
                    "output_path": output_path,
                    "attempts": result.get("attempts", 1)
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"代码生成失败: {e}"
            }

    def _extract_code(self, text: str) -> str:
        """提取代码部分"""
        # 去除 markdown 代码标记
        if "```python" in text:
            start = text.find("```python") + len("```python")
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        return text.strip()
