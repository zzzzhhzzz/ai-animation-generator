"""
协调器 Agent - 协调整个工作流程
"""

import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from llm.factory import create_llm

from .image_analyzer import ImageAnalyzer
from .script_writer import ScriptWriter
from .storyboard_writer import StoryboardWriter
from .code_generator import CodeGenerator
from .audio_producer import AudioProducer
from .reviewer import Reviewer
from validators import StoryboardValidator, ScriptValidator, CodeValidator

logger = logging.getLogger(__name__)


class Orchestrator:
    """工作流程协调器"""

    def __init__(self, provider: str = "openai", **kwargs):
        self.provider = provider
        self.llm = create_llm(provider, **kwargs)

        # 初始化各个 Agent
        self.image_analyzer = ImageAnalyzer(provider, **kwargs)
        self.script_writer = ScriptWriter(provider, **kwargs)
        self.storyboard_writer = StoryboardWriter(provider, **kwargs)
        self.code_generator = CodeGenerator(provider, **kwargs)
        self.audio_producer = AudioProducer()
        self.reviewer = Reviewer(provider, **kwargs)

        # 初始化验证器
        self.storyboard_validator = StoryboardValidator()
        self.script_validator = ScriptValidator()
        self.code_validator = CodeValidator()

        # 工作目录
        self.work_dir = "output"
        self.audio_dir = None
        self.code_path = None
        self.storyboard = None

    def run(self, requirement: str,
           image_path: str = None,
           mode: str = "full",
           output_dir: str = "output") -> Dict[str, Any]:
        """运行完整工作流程

        Args:
            requirement: 用户需求
            image_path: 图片路径（可选）
            mode: 运行模式 ("full", "simple", "storyboard_only")
            output_dir: 输出目录

        Returns:
            运行结果
        """
        self.work_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.audio_dir = os.path.join(output_dir, "audio")

        results = {
            "requirement": requirement,
            "image_path": image_path,
            "mode": mode,
            "steps": []
        }

        try:
            # 步骤1: 分析需求/图片
            if image_path and os.path.exists(image_path):
                analysis_result = self._analyze_image(image_path, requirement)
                results["steps"].append(("image_analysis", analysis_result))

                if not analysis_result.get("success"):
                    return {
                        "success": False,
                        "error": "图片分析失败",
                        "results": results
                    }

                # 使用分析结果作为需求
                requirement = analysis_result.get("analysis", requirement)

            # 步骤2: 生成脚本
            if mode in ("full", "simple"):
                script_result = self._generate_script(requirement)
                results["steps"].append(("script", script_result))

                if not script_result.get("success"):
                    return {
                        "success": False,
                        "error": "脚本生成失败",
                        "results": results
                    }

            # 步骤3: 生成分镜
            if mode == "full":
                storyboard_result = self._generate_storyboard(
                    script_result.get("script", requirement)
                )
            else:
                storyboard_result = self._generate_storyboard_simple(requirement)

            results["steps"].append(("storyboard", storyboard_result))

            if not storyboard_result.get("success"):
                return {
                    "success": False,
                    "error": "分镜生成失败",
                    "results": results
                }

            self.storyboard = storyboard_result.get("storyboard")

            # 保存分镜
            storyboard_path = os.path.join(output_dir, "storyboard.md")
            with open(storyboard_path, "w", encoding="utf-8") as f:
                f.write(self.storyboard)
            results["storyboard_path"] = storyboard_path

            # 步骤4: 生成音频
            audio_result = self._generate_audio()
            results["steps"].append(("audio", audio_result))

            # 步骤5: 生成代码
            code_result = self._generate_code()
            results["steps"].append(("code", code_result))

            if not code_result.get("success"):
                return {
                    "success": False,
                    "error": "代码生成失败",
                    "results": results
                }

            results["success"] = True
            results["output_dir"] = self.work_dir
            results["code_path"] = code_result.get("output_path", "")
            results["audio_dir"] = self.audio_dir

            return results

        except Exception as e:
            return {
                "success": False,
                "error": f"工作流程执行失败: {e}",
                "results": results
            }

    def _analyze_image(self, image_path: str, context: str = "") -> Dict[str, Any]:
        """分析图片"""
        print(f"[Orchestrator] 分析图片: {image_path}")
        return self.image_analyzer.analyze(image_path, context)

    def _generate_script(self, requirement: str) -> Dict[str, Any]:
        """生成脚本"""
        print("[Orchestrator] 生成脚本...")
        result = self.script_writer.write(requirement)

        # 验证脚本
        if result.get("success") and result.get("script"):
            self._validate_script(result["script"])
            attempts = result.get("attempts", 1)
            if attempts > 1:
                print(f"[Orchestrator] 脚本生成尝试次数: {attempts}")

        return result

    def _generate_storyboard(self, script: str) -> Dict[str, Any]:
        """生成分镜"""
        print("[Orchestrator] 生成分镜...")
        result = self.storyboard_writer.write(script)

        # 验证分镜
        if result.get("success") and result.get("storyboard"):
            self._validate_storyboard(result["storyboard"])
            attempts = result.get("attempts", 1)
            if attempts > 1:
                print(f"[Orchestrator] 分镜生成尝试次数: {attempts}")

        return result

    def _generate_storyboard_simple(self, requirement: str) -> Dict[str, Any]:
        """直接生成分镜（简化模式）"""
        print("[Orchestrator] 直接生成分镜...")
        result = self.storyboard_writer.write_simple(requirement)

        # 验证分镜
        if result.get("success") and result.get("storyboard"):
            self._validate_storyboard(result["storyboard"])
            attempts = result.get("attempts", 1)
            if attempts > 1:
                print(f"[Orchestrator] 分镜生成尝试次数: {attempts}")

        return result

    def _generate_audio(self) -> Dict[str, Any]:
        """生成音频"""
        print("[Orchestrator] 生成音频...")
        if not self.storyboard:
            return {"success": False, "error": "分镜不存在"}

        return self.audio_producer.produce_from_storyboard(
            self.storyboard,
            self.audio_dir
        )

    def _generate_code(self) -> Dict[str, Any]:
        """生成代码"""
        print("[Orchestrator] 生成代码...")
        if not self.storyboard:
            return {"success": False, "error": "分镜不存在"}

        code_path = os.path.join(self.work_dir, "script.py")
        result = self.code_generator.generate(
            self.storyboard,
            output_path=code_path
        )

        # 验证代码
        if result.get("success") and result.get("code"):
            self._validate_code(result["code"])
            attempts = result.get("attempts", 1)
            if attempts > 1:
                print(f"[Orchestrator] 代码生成尝试次数: {attempts}")

        return result

    def _validate_script(self, script: str) -> None:
        """验证脚本输出"""
        result = self.script_validator.validate(script)
        if result.warnings:
            logger.warning(f"脚本验证警告: {result.warnings}")
            print(f"[Orchestrator] 脚本验证警告: {result.warnings}")
        if not result.is_valid:
            logger.error(f"脚本验证失败: {result.errors}")
            print(f"[Orchestrator] 脚本验证失败: {result.errors}")

    def _validate_storyboard(self, storyboard: str) -> None:
        """验证分镜输出"""
        result = self.storyboard_validator.validate(storyboard)
        if result.warnings:
            logger.warning(f"分镜验证警告: {result.warnings}")
            print(f"[Orchestrator] 分镜验证警告: {result.warnings}")
        if not result.is_valid:
            logger.error(f"分镜验证失败: {result.errors}")
            print(f"[Orchestrator] 分镜验证失败: {result.errors}")

    def _validate_code(self, code: str) -> None:
        """验证代码输出"""
        result = self.code_validator.validate_code_syntax(code)
        if result.warnings:
            logger.warning(f"代码验证警告: {result.warnings}")
            print(f"[Orchestrator] 代码验证警告: {result.warnings}")
        if not result.is_valid:
            logger.error(f"代码验证失败: {result.errors}")
            print(f"[Orchestrator] 代码验证失败: {result.errors}")

    def review(self, video_path: str = None) -> Dict[str, Any]:
        """审核"""
        print("[Orchestrator] 审核...")

        audio_files = []
        if self.audio_dir and os.path.exists(self.audio_dir):
            audio_files = [os.path.join(self.audio_dir, f)
                         for f in os.listdir(self.audio_dir)
                         if f.endswith('.wav')]

        return self.reviewer.review(
            video_path=video_path,
            storyboard=self.storyboard,
            audio_files=audio_files
        )
