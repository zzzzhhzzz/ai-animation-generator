"""
图片理解 Agent - 使用视觉 LLM 分析图片
"""

from pathlib import Path
from typing import Optional, Dict, Any
from llm.factory import create_llm


class ImageAnalyzer:
    """图片理解 Agent"""

    SYSTEM_PROMPT = """你是一个专业的教学视频内容分析师。你擅长分析图片中的数学题目、几何图形、图表等信息。
请仔细分析用户提供的图片，提取以下信息：
1. 图片中的主要内容（题目、条件、图形等）
2. 关键信息（数值、符号、关系等）
3. 可能的解题思路（如果是题目）
请用简洁清晰的语言描述图片内容。"""

    def __init__(self, provider: str = "openai", **kwargs):
        self.llm = create_llm(provider, **kwargs)

    def analyze(self, image_path: str, additional_context: str = "") -> Dict[str, Any]:
        """分析图片

        Args:
            image_path: 图片路径
            additional_context: 额外上下文信息

        Returns:
            分析结果字典
        """
        # 如果没有图片路径，返回错误
        if not image_path or not Path(image_path).exists():
            return {
                "success": False,
                "error": f"图片文件不存在: {image_path}"
            }

        # 构建消息
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"{additional_context}\n\n请分析这张图片的内容。"
                    }
                ]
            }
        ]

        # 添加图片（OpenAI 格式）
        # 注意：实际使用需要根据 LLM 提供商调整格式
        try:
            import base64

            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_data}"
                }
            })
        except Exception as e:
            return {
                "success": False,
                "error": f"图片加载失败: {e}"
            }

        # 调用 LLM
        try:
            result = self.llm.provider.vision_chat(
                messages,
                model="gpt-4o"
            )

            return {
                "success": True,
                "analysis": result,
                "image_path": image_path
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"分析失败: {e}"
            }

    def analyze_simple(self, text_description: str) -> Dict[str, Any]:
        """简单文本分析（无需图片）

        Args:
            text_description: 文本描述

        Returns:
            分析结果
        """
        prompt = f"{self.SYSTEM_PROMPT}\n\n请分析以下内容：\n{text_description}"

        try:
            result = self.llm.chat(
                prompt,
                task_difficulty="hard",
                system_prompt=self.SYSTEM_PROMPT
            )

            return {
                "success": True,
                "analysis": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"分析失败: {e}"
            }
