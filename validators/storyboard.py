"""
分镜验证器 - 验证分镜输出的质量
"""

import re
import json
from typing import Any, Dict, List, Optional
from .base import BaseValidator, ValidationResult


class StoryboardValidator(BaseValidator):
    """分镜验证器"""

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["基本信息", "分镜设计", "音频生成清单"],
            "properties": {
                "基本信息": {
                    "type": "object",
                    "required": ["标题", "类型", "时长预估"],
                    "properties": {
                        "标题": {"type": "string", "minLength": 1},
                        "类型": {"type": "string", "enum": ["科普", "教学", "故事", "宣传"]},
                        "时长预估": {"type": "string", "pattern": r"约\d+分钟"},
                        "目标受众": {"type": "string"},
                        "风格要求": {"type": "string"}
                    }
                },
                "分镜设计": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["幕号", "画面描述", "字幕", "读白"],
                        "properties": {
                            "幕号": {"type": "integer"},
                            "幕名": {"type": "string"},
                            "画面描述": {"type": "string", "minLength": 5},
                            "字幕": {"type": "string", "maxLength": 20},
                            "读白": {"type": "string", "minLength": 5},
                            "动画时序": {"type": "string"},
                            "配音情感": {"type": "string"}
                        }
                    }
                },
                "音频生成清单": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["幕号", "文件名", "读白文本"],
                        "properties": {
                            "幕号": {"type": "integer"},
                            "文件名": {"type": "string", "pattern": r"audio_\d+_.*\.wav"},
                            "读白文本": {"type": "string", "minLength": 1}
                        }
                    }
                }
            }
        }

    def extract_output(self, text: str) -> Optional[Dict[str, Any]]:
        """从文本中提取分镜数据"""
        # 尝试从 markdown code block 中提取 JSON
        json_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试直接解析整个文本为 JSON
        # 去除可能的 markdown 标记
        clean_text = text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.split("\n")
            if len(lines) > 1:
                clean_text = "\n".join(lines[1:-1] if clean_text.endswith("```") else lines[1:])

        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            pass

        # 尝试从markdown格式中提取
        return self._parse_markdown(text)

    def _parse_markdown(self, text: str) -> Optional[Dict[str, Any]]:
        """从 markdown 格式中提取分镜数据"""
        data = {
            "基本信息": {},
            "分镜设计": [],
            "音频生成清单": []
        }

        # 解析基本信息
        basic_info_match = re.search(
            r"##\s*基本信息\s*(.*?)(?=##|\Z)",
            text, re.DOTALL
        )
        if basic_info_match:
            basic_section = basic_info_match.group(1)
            # 提取字段
            title_match = re.search(r"[-标题title：:]\s*(.+?)(?:\n|$)", basic_section)
            if title_match:
                data["基本信息"]["标题"] = title_match.group(1).strip()

            type_match = re.search(r"[-类型type：:]\s*(.+?)(?:\n|$)", basic_section)
            if type_match:
                data["基本信息"]["类型"] = type_match.group(1).strip()

            duration_match = re.search(r"[-时长duration：:]\s*(.+?)(?:\n|$)", basic_section)
            if duration_match:
                data["基本信息"]["时长预估"] = duration_match.group(1).strip()

        # 解析分镜设计
        scenes_match = re.search(
            r"##\s*分镜设计\s*(.*?)(?=##|\Z)",
            text, re.DOTALL
        )
        if scenes_match:
            scenes_section = scenes_match.group(1)
            # 按幕分割
            scene_pattern = r"###\s*(?:第\s*)?(\d+)\s*[幕场]\s*[:：]?\s*(.+?)(?=\n###|\Z)"
            for match in re.finditer(scene_pattern, scenes_section, re.DOTALL):
                scene_num = int(match.group(1))
                scene_content = match.group(2)

                scene_data = {
                    "幕号": scene_num,
                    "画面描述": "",
                    "字幕": "",
                    "读白": ""
                }

                # 提取字段
                desc_match = re.search(r"[-画面描述：:]\s*(.+?)(?:\n[-]|$)", scene_content, re.DOTALL)
                if desc_match:
                    scene_data["画面描述"] = desc_match.group(1).strip()

                subtitle_match = re.search(r"[-字幕subtitle：:]\s*(.+?)(?:\n[-]|$)", scene_content, re.DOTALL)
                if subtitle_match:
                    scene_data["字幕"] = subtitle_match.group(1).strip()

                narration_match = re.search(r"[-读白配音：:]\s*(.+?)(?:\n[-]|$)", scene_content, re.DOTALL)
                if narration_match:
                    scene_data["读白"] = narration_match.group(1).strip()

                data["分镜设计"].append(scene_data)

        # 解析音频清单
        audio_match = re.search(
            r"##\s*音频生成清单\s*(.*?)(?=##|\Z)",
            text, re.DOTALL
        )
        if audio_match:
            audio_section = audio_match.group(1)
            # 简单解析表格
            lines = audio_section.strip().split("\n")
            for line in lines:
                if "|" in line and "幕号" not in line and "---" not in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 3:
                        try:
                            audio_data = {
                                "幕号": int(parts[1]) if parts[1].isdigit() else 0,
                                "文件名": parts[2] if len(parts) > 2 else "",
                                "读白文本": parts[3] if len(parts) > 3 else ""
                            }
                            data["音频生成清单"].append(audio_data)
                        except (ValueError, IndexError):
                            pass

        return data if any([data["基本信息"], data["分镜设计"], data["音频生成清单"]]) else None

    def _validate_business_rules(self, data: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """验证业务规则"""
        errors = []
        warnings = []

        # 验证分镜数量
        scenes = data.get("分镜设计", [])
        if len(scenes) == 0:
            errors.append("分镜设计不能为空")
        elif len(scenes) > 10:
            warnings.append(f"分镜数量较多: {len(scenes)} 幕")

        # 验证字幕长度
        for i, scene in enumerate(scenes, 1):
            subtitle = scene.get("字幕", "")
            if len(subtitle) > 20:
                errors.append(f"第 {i} 幕字幕超过20字: {len(subtitle)}字")

            narration = scene.get("读白", "")
            if len(narration) < 5:
                warnings.append(f"第 {i} 幕读白较短: {len(narration)}字")

        # 验证音频清单完整性
        audio_list = data.get("音频生成清单", [])
        if len(audio_list) != len(scenes):
            warnings.append(
                f"音频清单数量({len(audio_list)})与分镜数量({len(scenes)})不匹配"
            )

        # 验证幕号连续性
        scene_numbers = [s.get("幕号", i+1) for i, s in enumerate(scenes)]
        expected = list(range(1, len(scenes) + 1))
        if sorted(scene_numbers) != expected:
            warnings.append("幕号不连续")

        return errors, warnings

    def get_few_shot_examples(self) -> str:
        return """
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
5. 幕号必须从1开始连续编号"""

    def get_self_check_prompt(self) -> str:
        return """
## 自检清单（输出前检查）：
- [ ] 基本信息是否完整（标题、类型、时长预估）？
- [ ] 字幕是否 ≤20 字？
- [ ] 读白是否 ≥5 字？
- [ ] 每幕是否都有画面描述、字幕、读白？
- [ ] 音频清单是否与分镜数量一致？
- [ ] 幕号是否从1开始连续？
- [ ] JSON 格式是否正确？

如果有任何一项不满足，请修正后再输出。"""
