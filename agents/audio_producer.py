"""
音频制作 Agent - 使用 Edge TTS 生成语音
"""

import os
import asyncio
import csv
from typing import Dict, Any, List, Optional
from pathlib import Path


class AudioProducer:
    """音频制作 Agent"""

    VOICE_MAP = {
        'xiaoxiao': 'zh-CN-XiaoxiaoNeural',
        'xiaoyi': 'zh-CN-XiaoyiNeural',
        'yunyang': 'zh-CN-YunyangNeural',
        'yunjian': 'zh-CN-YunjianNeural',
    }

    def __init__(self):
        self.edge_tts_available = True
        try:
            import edge_tts
        except ImportError:
            self.edge_tts_available = False
            print("Warning: edge-tts not installed, audio generation will be limited")

    def produce_from_storyboard(self, storyboard: str,
                              output_dir: str = "audio",
                              voice: str = "xiaoxiao") -> Dict[str, Any]:
        """从分镜脚本生成音频

        Args:
            storyboard: 分镜脚本
            output_dir: 输出目录
            voice: 声音选择

        Returns:
            生成结果
        """
        if not self.edge_tts_available:
            return {
                "success": False,
                "error": "edge-tts 未安装"
            }

        # 解析分镜获取音频列表
        audio_list = self._parse_audio_list(storyboard)

        if not audio_list:
            return {
                "success": False,
                "error": "未能从分镜中提取音频列表"
            }

        # 生成音频
        return self._generate_audio(audio_list, output_dir, voice)

    def produce_from_texts(self, texts: List[Dict[str, str]],
                          output_dir: str = "audio",
                          voice: str = "xiaoxiao") -> Dict[str, Any]:
        """从文本列表生成音频

        Args:
            texts: 文本列表 [{"filename": "xxx.wav", "text": "..."}]
            output_dir: 输出目录
            voice: 声音选择

        Returns:
            生成结果
        """
        if not self.edge_tts_available:
            return {
                "success": False,
                "error": "edge-tts 未安装"
            }

        return self._generate_audio(texts, output_dir, voice)

    def _parse_audio_list(self, storyboard: str) -> List[Dict[str, str]]:
        """解析分镜脚本提取音频列表"""
        import re

        audio_list = []
        lines = storyboard.split('\n')

        # 查找音频清单表格
        in_audio_section = False
        for i, line in enumerate(lines):
            if '音频生成清单' in line:
                in_audio_section = True
                continue

            if in_audio_section:
                if line.startswith('|') and '---' not in line:
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 2 and parts[0] != '幕号':
                        # 尝试解析表格行
                        filename = parts[1] if len(parts) > 1 else ""
                        text = parts[2] if len(parts) > 2 else ""
                        if filename and text:
                            audio_list.append({
                                "filename": filename,
                                "text": text.strip('"')
                            })
                elif line.startswith('##') or line.strip() == '':
                    if len(audio_list) > 0:
                        break

        # 如果没有找到表格，尝试从读白字段提取
        if not audio_list:
            scene_pattern = r'###\s+[第幕\d]+\s*[:：]?\s*(.+?)(?:\n|$)'
            read白_pattern = r'读白[:：]\s*(.+?)(?:\n|$)'

            scenes = re.findall(scene_pattern, storyboard)
            for i, scene in enumerate(scenes, 1):
                match = re.search(read白_pattern, storyboard)
                if match:
                    audio_list.append({
                        "filename": f"audio_{i:03d}_{scene.strip()}.wav",
                        "text": match.group(1).strip()
                    })

        return audio_list

    def _generate_audio(self, audio_list: List[Dict[str, str]],
                       output_dir: str,
                       voice: str) -> Dict[str, Any]:
        """生成音频文件"""
        import edge_tts

        os.makedirs(output_dir, exist_ok=True)

        voice_id = self.VOICE_MAP.get(voice, self.VOICE_MAP['xiaoxiao'])

        async def generate_one(item):
            try:
                communicate = edge_tts.Communicate(item["text"], voice_id)
                output_path = os.path.join(output_dir, item["filename"])
                await communicate.save(output_path)
                return {
                    "filename": item["filename"],
                    "success": True,
                    "path": output_path
                }
            except Exception as e:
                return {
                    "filename": item["filename"],
                    "success": False,
                    "error": str(e)
                }

        async def generate_all():
            tasks = [generate_one(item) for item in audio_list]
            return await asyncio.gather(*tasks)

        results = asyncio.run(generate_all())

        success_count = sum(1 for r in results if r.get("success"))

        return {
            "success": success_count > 0,
            "total": len(audio_list),
            "success_count": success_count,
            "results": results,
            "output_dir": output_dir
        }

    def get_audio_info(self, audio_dir: str) -> Dict[str, Any]:
        """获取音频信息"""
        if not os.path.exists(audio_dir):
            return {"success": False, "error": "目录不存在"}

        audio_files = [f for f in os.listdir(audio_dir) if f.endswith('.wav')]

        return {
            "success": True,
            "count": len(audio_files),
            "files": audio_files
        }
