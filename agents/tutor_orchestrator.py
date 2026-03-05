"""
Tutor 工作流协调器 - 完整的数学辅导视频生成系统

遵循 8 步工作流：
1. 数学建模分析
2. HTML + SVG 可视化
3. 分镜脚本生成
4. TTS 语音生成
5. 验证并更新时长
6. 生成脚手架代码
7. 生成完整 Manim 代码
8. 代码检查与渲染
"""

import os
import json
import asyncio
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from llm.factory import create_llm
from validators import StoryboardValidator, CodeValidator

from .math_analyzer import MathAnalyzer
from .html_visualizer import HTMLVisualizer
from .storyboard_writer import StoryboardWriter
from .code_generator import CodeGenerator
from .audio_producer import AudioProducer


class TutorOrchestrator:
    """数学辅导视频生成工作流协调器"""

    WORKFLOW_STEPS = [
        "math_analysis",      # 1. 数学建模分析
        "html_visualization", # 2. HTML 可视化
        "storyboard",         # 3. 分镜脚本
        "tts_generation",    # 4. TTS 语音生成
        "validation",        # 5. 验证更新
        "scaffold",          # 6. 脚手架代码
        "implementation",    # 7. 完整代码
        "render",            # 8. 渲染视频
    ]

    def __init__(self, provider: str = "openai", **kwargs):
        self.provider = provider
        self.llm = create_llm(provider, **kwargs)

        # 初始化各个模块
        self.math_analyzer = MathAnalyzer(provider, **kwargs)
        self.html_visualizer = HTMLVisualizer(provider, **kwargs)
        self.storyboard_writer = StoryboardWriter(provider, **kwargs)
        self.code_generator = CodeGenerator(provider, **kwargs)
        self.audio_producer = AudioProducer()

        # 验证器
        self.storyboard_validator = StoryboardValidator()
        self.code_validator = CodeValidator()

        # 工作目录
        self.work_dir = "tutor_output"
        self.audio_dir = None

        # 工作流状态
        self.state: Dict[str, Any] = {
            "problem": "",
            "math_analysis": None,
            "html_file": None,
            "storyboard_file": None,
            "audio_info": None,
            "scaffold_file": None,
            "script_file": None,
            "video_file": None,
            "completed_steps": [],
        }

    def run(self, problem: str,
            image_path: str = None,
            output_dir: str = "tutor_output",
            start_step: int = 1,
            end_step: int = 8) -> Dict[str, Any]:
        """运行完整工作流

        Args:
            problem: 数学题目（文本或图片描述）
            image_path: 题目图片路径（可选）
            output_dir: 输出目录
            start_step: 起始步骤（1-8）
            end_step: 结束步骤（1-8）

        Returns:
            工作流执行结果
        """
        self.work_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.audio_dir = os.path.join(output_dir, "audio")
        self.state["problem"] = problem

        print("=" * 60)
        print("数学辅导视频生成系统")
        print("=" * 60)
        print(f"题目: {problem[:50]}...")
        print(f"步骤: {start_step} → {end_step}")
        print()

        results = {
            "success": False,
            "problem": problem,
            "steps": {},
            "output_dir": output_dir,
        }

        try:
            # 步骤 1: 数学分析
            if start_step <= 1 <= end_step:
                step_result = self.step_math_analysis(problem, image_path)
                results["steps"]["math_analysis"] = step_result
                if not step_result.get("success"):
                    return self._fail(results, "数学分析失败")
                self.state["math_analysis"] = step_result.get("analysis")

            # 步骤 2: HTML 可视化
            if start_step <= 2 <= end_step:
                step_result = self.step_html_visualization(
                    self.state["math_analysis"]
                )
                results["steps"]["html_visualization"] = step_result
                if not step_result.get("success"):
                    return self._fail(results, "HTML可视化失败")
                self.state["html_file"] = step_result.get("html_file")

            # 步骤 3: 分镜脚本
            if start_step <= 3 <= end_step:
                html_content = self.state.get("html_file", "")
                step_result = self.step_storyboard(
                    self.state["math_analysis"],
                    html_content
                )
                results["steps"]["storyboard"] = step_result
                if not step_result.get("success"):
                    return self._fail(results, "分镜脚本生成失败")
                self.state["storyboard_file"] = step_result.get("storyboard")

            # 步骤 4: TTS 语音
            if start_step <= 4 <= end_step:
                step_result = self.step_tts_generation(
                    self.state["storyboard_file"]
                )
                results["steps"]["tts_generation"] = step_result
                if not step_result.get("success"):
                    return self._fail(results, "TTS生成失败")
                self.state["audio_info"] = step_result.get("audio_info")

            # 步骤 5: 验证更新
            if start_step <= 5 <= end_step:
                step_result = self.step_validation(
                    self.state["storyboard_file"],
                    self.state["audio_info"]
                )
                results["steps"]["validation"] = step_result
                if not step_result.get("success"):
                    return self._fail(results, "验证失败")

            # 步骤 6: 脚手架
            if start_step <= 6 <= end_step:
                step_result = self.step_scaffold(
                    self.state["storyboard_file"],
                    self.state["audio_info"]
                )
                results["steps"]["scaffold"] = step_result
                if not step_result.get("success"):
                    return self._fail(results, "脚手架生成失败")
                self.state["scaffold_file"] = step_result.get("scaffold")

            # 步骤 7: 完整代码
            if start_step <= 7 <= end_step:
                step_result = self.step_implementation(
                    self.state["scaffold_file"],
                    self.state["storyboard_file"],
                    self.state["audio_info"]
                )
                results["steps"]["implementation"] = step_result
                if not step_result.get("success"):
                    return self._fail(results, "代码生成失败")
                self.state["script_file"] = step_result.get("script_file")

            # 步骤 8: 渲染
            if start_step <= 8 <= end_step:
                step_result = self.step_render(self.state["script_file"])
                results["steps"]["render"] = step_result
                if not step_result.get("success"):
                    return self._fail(results, "渲染失败")
                self.state["video_file"] = step_result.get("video_file")

            results["success"] = True
            results["state"] = self.state

            print()
            print("=" * 60)
            print("生成完成!")
            print("=" * 60)
            self._print_results(results)

            return results

        except Exception as e:
            return self._fail(results, f"工作流执行失败: {e}")

    def _fail(self, results: Dict, error: str) -> Dict:
        """处理失败"""
        results["success"] = False
        results["error"] = error
        print(f"错误: {error}")
        return results

    def _print_results(self, results: Dict):
        """打印结果"""
        if results.get("math_analysis"):
            print(f"数学分析: ✓")
        if results.get("html_file"):
            print(f"HTML可视化: ✓")
        if results.get("storyboard_file"):
            print(f"分镜脚本: ✓")
        if results.get("audio_info"):
            print(f"音频文件: {len(results['audio_info'].get('files', []))}个")
        if results.get("script_file"):
            print(f"代码文件: ✓")
        if results.get("video_file"):
            print(f"视频文件: {results['video_file']}")

    # ========== 步骤实现 ==========

    def step_math_analysis(self, problem: str, image_path: str = None) -> Dict[str, Any]:
        """步骤 1: 数学建模分析"""
        print("[步骤1] 数学建模分析...")

        if image_path and os.path.exists(image_path):
            result = self.math_analyzer.analyze_from_image(problem, image_path)
        else:
            result = self.math_analyzer.analyze(problem)

        if result.get("success"):
            # 保存分析结果
            analysis_file = os.path.join(self.work_dir, "math_analysis.md")
            with open(analysis_file, "w", encoding="utf-8") as f:
                f.write(result.get("analysis", ""))
            result["analysis_file"] = analysis_file

        return result

    def step_html_visualization(self, math_analysis: str) -> Dict[str, Any]:
        """步骤 2: HTML 可视化"""
        print("[步骤2] HTML + SVG 可视化...")

        result = self.html_visualizer.visualize(math_analysis)

        if result.get("success"):
            # 保存 HTML 文件
            date_str = datetime.now().strftime("%Y%m%d")
            html_file = os.path.join(self.work_dir, f"数学_{date_str}.html")
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(result.get("html", ""))
            result["html_file"] = html_file

        return result

    def step_storyboard(self, math_analysis: str, html_content: str = "") -> Dict[str, Any]:
        """步骤 3: 生成分镜脚本"""
        print("[步骤3] 生成分镜脚本...")

        result = self.storyboard_writer.write_from_math(
            math_analysis=math_analysis,
            html_content=html_content
        )

        if result.get("success"):
            # 保存分镜文件
            date_str = datetime.now().strftime("%Y%m%d")
            storyboard_file = os.path.join(
                self.work_dir,
                f"{date_str}_分镜.md"
            )
            with open(storyboard_file, "w", encoding="utf-8") as f:
                f.write(result.get("storyboard", ""))
            result["storyboard_file"] = storyboard_file

        return result

    def step_tts_generation(self, storyboard_file: str) -> Dict[str, Any]:
        """步骤 4: TTS 语音生成"""
        print("[步骤4] TTS 语音生成...")

        # 读取分镜脚本
        with open(storyboard_file, "r", encoding="utf-8") as f:
            storyboard = f.read()

        # 生成音频
        result = self.audio_producer.produce_from_storyboard(
            storyboard,
            self.audio_dir
        )

        # 保存 audio_info.json
        if result.get("success"):
            audio_info = {
                "files": [
                    {
                        "scene": i + 1,
                        "file": r.get("filename", ""),
                        "duration": 0  # 步骤5填充
                    }
                    for i, r in enumerate(result.get("results", []))
                ]
            }
            audio_info_file = os.path.join(self.audio_dir, "audio_info.json")
            with open(audio_info_file, "w", encoding="utf-8") as f:
                json.dump(audio_info, f, ensure_ascii=False, indent=2)
            result["audio_info"] = audio_info
            result["audio_info_file"] = audio_info_file

        return result

    def step_validation(self, storyboard_file: str, audio_info: Dict) -> Dict[str, Any]:
        """步骤 5: 验证并更新时长"""
        print("[步骤5] 验证音频并更新时长...")

        # 读取音频时长
        audio_info_file = os.path.join(self.audio_dir, "audio_info.json")
        if os.path.exists(audio_info_file):
            with open(audio_info_file, "r", encoding="utf-8") as f:
                audio_info = json.load(f)
        else:
            return {"success": False, "error": "audio_info.json 不存在"}

        # 获取每个音频文件的时长
        for audio_file in audio_info.get("files", []):
            file_path = os.path.join(self.audio_dir, audio_file["file"])
            if os.path.exists(file_path):
                duration = self._get_audio_duration(file_path)
                audio_file["duration"] = duration

        # 保存更新的 audio_info.json
        with open(audio_info_file, "w", encoding="utf-8") as f:
            json.dump(audio_info, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "audio_info": audio_info,
            "audio_info_file": audio_info_file
        }

    def _get_audio_duration(self, file_path: str) -> float:
        """获取音频文件时长"""
        try:
            from mutagen import File
            audio = File(file_path)
            if audio:
                return audio.info.length
        except:
            pass
        return 0

    def step_scaffold(self, storyboard_file: str, audio_info: Dict) -> Dict[str, Any]:
        """步骤 6: 生成脚手架代码"""
        print("[步骤6] 生成脚手架代码...")

        # 读取分镜脚本
        with open(storyboard_file, "r", encoding="utf-8") as f:
            storyboard = f.read()

        # 使用模板生成脚手架
        scaffold_file = os.path.join(self.work_dir, "script_scaffold.py")

        # 读取模板
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "templates",
            "script_scaffold.py"
        )

        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                scaffold_content = f.read()
        else:
            scaffold_content = self._generate_default_scaffold(storyboard, audio_info)

        # 保存脚手架
        with open(scaffold_file, "w", encoding="utf-8") as f:
            f.write(scaffold_content)

        return {
            "success": True,
            "scaffold_file": scaffold_file
        }

    def _generate_default_scaffold(self, storyboard: str, audio_info: Dict) -> str:
        """生成默认脚手架"""
        scenes = audio_info.get("files", [])
        scenes_str = ",\n        ".join([
            f'({s["scene"]}, "幕{s[\"scene\"]}", "{s[\"file\"]}", {s.get("duration", 0)})'
            for s in scenes
        ])

        return f'''"""数学教学视频脚手架"""
from manim import *
import json
import os

class MathScene(Scene):
    """数学教学视频场景"""

    COLORS = {{
        'background': '#1a1a2e',
        'primary': '#4ecca3',
        'secondary': '#e94560',
        'highlight': '#ffc107',
        'text': '#ffffff',
    }}

    SCENES = [
        {scenes_str}
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.audio_timings = self._load_audio_timings()

    def _load_audio_timings(self):
        """从 audio_info.json 加载音频时长"""
        try:
            with open("audio/audio_info.json", "r") as f:
                info = json.load(f)
            return {{item["file"]: item["duration"] for item in info["files"]}}
        except:
            return {{}}

    def calculate_geometry(self):
        """计算几何元素位置"""
        # TODO: 根据题目几何关系实现
        return {{}}

    def assert_geometry(self, geometry):
        """验证几何正确性"""
        # TODO: 验证题目条件
        pass

    def define_elements(self, geometry):
        """定义图形元素"""
        # TODO: 定义点、线、圆等
        return {{}}

    def construct(self):
        """主流程"""
        geometry = self.calculate_geometry()
        self.assert_geometry(geometry)
        elements = self.define_elements(geometry)
        self.camera.background_color = self.COLORS['background']

        for scene_num, scene_name, audio_file, duration in self.SCENES:
            self.play_scene(scene_num, scene_name, audio_file, duration, elements, geometry)

    def play_scene(self, scene_num, scene_name, audio_file, duration, elements, geometry):
        """播放单幕"""
        # TODO: 实现动画
        pass
'''

    def step_implementation(self, scaffold_file: str, storyboard_file: str,
                           audio_info: Dict) -> Dict[str, Any]:
        """步骤 7: 生成完整代码"""
        print("[步骤7] 生成完整代码...")

        # 读取脚手架
        with open(scaffold_file, "r", encoding="utf-8") as f:
            scaffold = f.read()

        # 读取分镜
        with open(storyboard_file, "r", encoding="utf-8") as f:
            storyboard = f.read()

        # 使用 CodeGenerator 生成完整代码
        result = self.code_generator.generate_from_scaffold(
            scaffold=scaffold,
            storyboard=storyboard,
            audio_info=audio_info,
            output_path=os.path.join(self.work_dir, "script.py")
        )

        return result

    def step_render(self, script_file: str) -> Dict[str, Any]:
        """步骤 8: 代码检查与渲染"""
        print("[步骤8] 代码检查与渲染...")

        # 检查代码结构
        check_result = self._check_script(script_file)
        if not check_result["success"]:
            return check_result

        # 渲染视频
        video_file = self._render_video(script_file)

        return {
            "success": True,
            "video_file": video_file
        }

    def _check_script(self, script_file: str) -> Dict[str, Any]:
        """检查代码结构"""
        print("  [检查] 代码结构检查...")

        try:
            # 尝试编译
            import py_compile
            py_compile.compile(script_file, doraise=True)

            # 检查必要函数
            with open(script_file, "r") as f:
                content = f.read()

            checks = {
                "calculate_geometry": "calculate_geometry" in content,
                "assert_geometry": "assert_geometry" in content,
                "define_elements": "define_elements" in content,
                "add_sound": "add_sound" in content,
            }

            failed = [k for k, v in checks.items() if not v]
            if failed:
                return {
                    "success": False,
                    "error": f"缺少必要函数: {', '.join(failed)}"
                }

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": f"代码检查失败: {e}"}

    def _render_video(self, script_file: str) -> str:
        """渲染视频"""
        print("  [渲染] 生成视频...")

        # 切换到工作目录
        old_dir = os.getcwd()
        os.chdir(self.work_dir)

        try:
            # 使用 manim 渲染
            cmd = [
                "python", "-m", "manim",
                "-pql",  # 低质量快速预览
                script_file,
                "MathScene"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"  警告: 渲染有错误但继续: {result.stderr}")

            # 查找生成的文件
            video_path = os.path.join(
                self.work_dir,
                "media",
                "videos",
                "script",
                "480p15",
                "MathScene.mp4"
            )

            if os.path.exists(video_path):
                # 拷贝到根目录
                final_path = os.path.join(self.work_dir, "MathScene.mp4")
                import shutil
                shutil.copy2(video_path, final_path)
                return final_path

            return video_path

        finally:
            os.chdir(old_dir)
