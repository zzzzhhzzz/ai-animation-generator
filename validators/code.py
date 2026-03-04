"""
代码验证器 - 验证生成的 Manim 代码质量
"""

import re
import ast
from typing import Any, Dict, List, Optional
from .base import BaseValidator, ValidationResult


class CodeValidator(BaseValidator):
    """Manim 代码验证器"""

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["code", "scenes"],
            "properties": {
                "code": {"type": "string", "minLength": 50},
                "scenes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["scene_name", "audio_file"],
                        "properties": {
                            "scene_name": {"type": "string"},
                            "audio_file": {"type": "string", "pattern": r".*\.wav"}
                        }
                    }
                }
            }
        }

    def extract_output(self, text: str) -> Optional[Dict[str, Any]]:
        """从文本中提取代码数据"""
        # 提取代码块
        code_pattern = r"```(?:python)?\s*(.*?)```"
        match = re.search(code_pattern, text, re.DOTALL)
        if match:
            code = match.group(1).strip()
            return {
                "code": code,
                "scenes": self._extract_scenes(code)
            }
        return None

    def _extract_scenes(self, code: str) -> List[Dict[str, Any]]:
        """从代码中提取场景信息"""
        scenes = []

        # 查找 Scene 类
        class_pattern = r"class\s+(\w+)\s*\(\s*Scene\s*\)"
        for match in re.finditer(class_pattern, code):
            scene_name = match.group(1)

            # 查找对应的音频文件
            audio_pattern = rf"class\s+{scene_name}.*?add_sound\s*\(\s*[\"']([^\"']+)[\"']"
            audio_match = re.search(audio_pattern, code, re.DOTALL)

            scenes.append({
                "scene_name": scene_name,
                "audio_file": audio_match.group(1) if audio_match else ""
            })

        return scenes

    def _validate_business_rules(self, data: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """验证代码业务规则"""
        errors = []
        warnings = []

        code = data.get("code", "")

        # 检查必要的导入
        if "from manim import" not in code and "import manim" not in code:
            errors.append("缺少 manim 导入")

        # 检查 Scene 类定义
        if "class " not in code or "Scene" not in code:
            errors.append("缺少 Scene 类定义")

        # 检查 construct 方法
        if "def construct" not in code:
            errors.append("缺少 construct 方法")

        # 检查音频文件路径格式
        audio_files = re.findall(r'add_sound\s*\(\s*["\']([^"\']+)["\']', code)
        for audio_file in audio_files:
            if not audio_file.endswith(".wav"):
                warnings.append(f"音频文件格式可能不正确: {audio_file}")
            if not audio_file.startswith("audio/") and not audio_file.startswith("./"):
                warnings.append(f"音频文件路径建议使用相对路径: {audio_file}")

        # 检查语法错误
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Python 语法错误: {e}")

        # 检查中文字体支持
        if "Text(" in code and "font" not in code.lower():
            warnings.append("使用 Text 对象但未指定字体，可能不支持中文")

        # 检查颜色方案
        if "#" not in code:
            warnings.append("未发现颜色定义，可能影响视觉效果")

        return errors, warnings

    def validate_code_syntax(self, code: str) -> ValidationResult:
        """专门验证代码语法"""
        errors = []
        warnings = []

        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"语法错误: {e.lineno}: {e.msg}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def validate_code_imports(self, code: str) -> ValidationResult:
        """验证代码导入"""
        errors = []
        warnings = []

        # 必需导入
        required_imports = ["manim", "Scene"]
        for imp in required_imports:
            if imp not in code:
                errors.append(f"缺少必要导入: {imp}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def get_few_shot_examples(self) -> str:
        return """
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
5. 建议指定字体以支持中文"""

    def get_self_check_prompt(self) -> str:
        return """
## 自检清单（输出前检查）：
- [ ] 是否导入了 manim？
- [ ] 是否有 Scene 类定义？
- [ ] 是否有 construct 方法？
- [ ] 音频路径格式是否正确（audio/xxx.wav）？
- [ ] Python 语法是否正确？
- [ ] 是否指定了字体（支持中文）？
- [ ] 代码是否完整可运行？

如果有任何一项不满足，请修正后再输出。"""
