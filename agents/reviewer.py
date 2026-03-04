"""
审核 Agent - 审核生成的视频内容
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from llm.factory import create_llm


class Reviewer:
    """视频审核 Agent"""

    SYSTEM_PROMPT = """你是一个专业的视频内容审核员。你擅长审核教学视频的质量，包括：
1. 内容准确性
2. 画面质量
3. 音画同步
4. 动画流畅度
5. 知识点讲解清晰度

请对生成的视频进行审核，并提供具体的改进建议。"""

    def __init__(self, provider: str = "openai", **kwargs):
        self.llm = create_llm(provider, **kwargs)

    def review(self, video_path: str = None,
              storyboard: str = None,
              code: str = None,
              audio_files: List[str] = None) -> Dict[str, Any]:
        """审核视频

        Args:
            video_path: 视频文件路径
            storyboard: 分镜脚本
            code: 动画代码
            audio_files: 音频文件列表

        Returns:
            审核结果
        """
        # 构建审核信息
        review_items = []

        if video_path and os.path.exists(video_path):
            review_items.append(f"视频文件: {video_path}")
            review_items.append(f"文件大小: {os.path.getsize(video_path) / 1024 / 1024:.2f} MB")

        if storyboard:
            review_items.append(f"\n分镜脚本:\n{storyboard[:500]}...")

        if code:
            review_items.append(f"\n动画代码:\n{code[:500]}...")

        if audio_files:
            review_items.append(f"\n音频文件: {', '.join(audio_files)}")

        prompt = f"""请对以下动画视频项目进行审核：

{chr(10).join(review_items)}

请检查：
1. 音频文件是否完整
2. 代码是否可运行
3. 分镜是否完整
4. 是否有明显的错误

请提供详细的审核报告，包括：
- 通过项
- 问题项（如有）
- 改进建议（如有）

直接输出审核报告，不要有其他格式。"""

        try:
            result = self.llm.chat(
                prompt,
                task_difficulty="hard",
                system_prompt=self.SYSTEM_PROMPT,
                max_tokens=2000
            )

            return {
                "success": True,
                "review": result,
                "video_path": video_path,
                "has_video": video_path and os.path.exists(video_path)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"审核失败: {e}"
            }

    def review_code(self, code: str) -> Dict[str, Any]:
        """审核代码

        Args:
            code: 动画代码

        Returns:
            审核结果
        """
        prompt = f"""请审核以下 Manim 动画代码：

```python
{code}
```

请检查：
1. 代码完整性（导入、类定义、方法等）
2. 语法正确性
3. 音频集成是否正确
4. 动画时长是否合理
5. 是否有明显的错误

直接输出审核结果。"""

        try:
            result = self.llm.chat(
                prompt,
                task_difficulty="hard",
                system_prompt=self.SYSTEM_PROMPT,
                max_tokens=1500
            )

            return {
                "success": True,
                "review": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"审核失败: {e}"
            }
